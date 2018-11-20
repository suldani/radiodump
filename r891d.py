#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
제목
Dump_KBS_Radio

설명
KBS라디오 DirectScream 저장하며 daemon처럼 운영한다.
오픈스튜디오이면 mp4로 영상, 아니면 m4a로 오디오만 저장한다.
저장중 네트웍이상, 정전 등의 오류 발생시에도 저장되도록 함.
Asus Router에서 entware, ffmpeg, python의 라이브러리를 사용

주의. 
1. kbs측 스트리밍 데이터의 캐시(추정)로 일찍 녹화가 시작된다. 
시간을 정확하게 맞추고 싶다면 녹화시간을 15~20초정도 앞당길것
2. sh(ash)과 python의 시각이 지역경도만큼의 차이가 있다.(9시간)
3. 라디오 정보를 가져오는 중 오류가 생기면 강제종료.
4. 20180809 현재 화질 500Kbps이며 그 이하로 저장시엔 Router reboot.

실행
1. 대몬 : nohup recd.py >/dev/null 2>&1 &
2. 1회  : recd.py [ 시작시간[HHMMSS] 종료시간[HHMMSS] ]

daemon설치방법
1. /jffs/scripts/post-mount 파일에 아래 내용 추가
        cru a "execute recd" "50 19 * * * /opt/usr/recd.py >/dev/null 2>&1"
        cru a "kill    recd" "49 19 * * * killall python"
        /opt/usr/recd.py >/dev/null 2>&1
2. /jffs/scripts/unmount 파일에 아래 내용 추가
        killall python
3. reboot 후 ps | grep python으로 실행중인지 확인한다.
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# 목195740 215740
#######################################################################
cfg_dft_name      = u'AKMU_Suhyun VolumeUp'
cfg_bora_url      = 'http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=25&ch_type=radioList'
#cfg_program_code = 'R2018-0086'
cfg_program_stime = '200000'
cfg_temp_dir      = '/opt/usr/'
cfg_target_dir    = '/mnt/WD8TB/_AKMU/6-2.RadioDJ_VolumeUp/'
cfg_stt_time      = '195320' #시낙믿
cfg_end_time      = '215900' #시낙믿
#cfg_stt_time      = '195740'
#cfg_end_time      = '215700'
cfg_hb_seconds    = 60
#######################################################################

# pip install module
import requests
import re
import json
import datetime
import time
import os
import sys
import logging
import logging.handlers
from bs4      import BeautifulSoup
from pytz     import timezone


def init_log(bFile,bScrn) :
	# 로거 생성
	logger = logging.getLogger('main')
	logger.setLevel(logging.DEBUG)

	# 파일 핸들러 생성
	log_file  = logging.handlers.RotatingFileHandler( sys.argv[0][:-2]+'log' , 1*1024*1024 , 1 ) #1메가, 1회
	log_scrn  = logging.StreamHandler()

	# 포맷터 생성 & 핸들러에 등록
	formatter = logging.Formatter('%(asctime)s [%(lineno)03d:%(levelname)7s] %(message)s ')
	log_file.setFormatter(formatter)
	log_scrn.setFormatter(formatter)

	# 핸들러를 로거에 등록, 다수의 핸들러를 등록할 수 있다.
	if bFile :
		logger.addHandler(log_file)
	if bScrn :
		logger.addHandler(log_scrn)
	return logger


def rec_kbs_radio( rec_stt_time , rec_end_time ) :
	#0. 공유기, py시각과 cron(sh)시각의 보정
	nNow = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%H%M%S')
#	logger.info( "녹회시작시간 [%s] 녹화종료시간 [%s] 현재시간 [%s]" , rec_stt_time , rec_end_time , nNow )


	#0. 예외처리(방송시간이 아닌 경우 방송 시간까지 대기)
	if( int(nNow) >= int(rec_end_time) or int(nNow) < int(rec_stt_time) ) :
		sleep_time = int(( datetime.datetime.strptime( rec_stt_time , '%H%M%S' )
		                 - datetime.datetime.strptime( nNow         , '%H%M%S' )
						 ).total_seconds()
						)
		sleep_time = sleep_time + ( 0 if( sleep_time >= 0 ) else 86400 )
		logger.info( "시작[%6s] 종료[%6s] 현재[%6s]. [%5d]초 후 녹화합니다." , rec_stt_time , rec_end_time , nNow , sleep_time )
		time.sleep( cfg_hb_seconds if( sleep_time > cfg_hb_seconds ) else sleep_time )
		return sleep_time


	#1. KBS CoolFM 원천정보 획득
	try :
		bora_html = requests.get(cfg_bora_url)
		bora_soup = BeautifulSoup(bora_html.text, 'html.parser')
	except :
		logger.error( "원천정보를 가져오는 중 오류가 발생했습니다." )
		return -1


	#1-1. 원천정보에서 오픈스튜디오 정보 설정
	try :
		schl_rinf = re.findall(r'var table = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		schl_jinf = json.loads(schl_rinf.replace('\\',''))
		radio_open_studio = 0
		for i in range( len ( schl_jinf['data'] ) ) :
			if schl_jinf['data'][i]['program_stime'] == cfg_program_stime :
				if schl_jinf['data'][i]['radio_open_studio_yn'] == 'Y' :
					radio_open_studio = 1
				break
	except :
		logger.error( "오픈스튜디오 정보 파싱에서 실패했습니다." )
		return -2


	#1-2. 원천정보에서 스트리밍 정보 설정
	try :
		scrm_rdat = re.findall(r'var channel = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		scrm_jdat = json.loads(scrm_rdat.replace('\\',''))
		rec_url  = scrm_jdat['channel_item'][radio_open_studio]['service_url']                                                     # 보라url
		rec_ddtm = scrm_jdat['cached_datetime'][2:10].replace('-','') + "_" + scrm_jdat[u'cached_datetime'][11:].replace(':','')   # 날짜
	except :
		logger.error( "스트리밍 정보 파싱에서 실패했습니다." )
		return -3


	#3. 라디오or보라별 스트리밍 정보 설정
	rec_flnm = rec_ddtm + " " + cfg_dft_name + (".mp4" if ( radio_open_studio == 1 ) else ".m4a")                              # 파일명
	rec_time = int((datetime.datetime.strptime( rec_end_time , '%H%M%S' ) - datetime.datetime.strptime( nNow , '%H%M%S' )).total_seconds())
	rec_call = ( "/opt/bin/ffmpeg -i \"%s\" -y -t %d -c copy %s\"%s\"" ) % ( rec_url , rec_time , cfg_temp_dir , rec_flnm ) #  -loglevel error
	logger.info( ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::" )
	logger.info( "Recoding_info : rec_call [%s]" % rec_call )
	logger.info( "Recoding_info : rec_url  [%s]" % rec_url  )
	logger.info( "Recoding_info : rec_ddtm [%s]" % rec_ddtm )
	logger.info( "Recoding_info : rec_flnm [%s]" % rec_flnm )
	logger.info( "Recoding_info : rec_time [%s]" % rec_time )
	logger.info( "Start Recoding..." )


	#4. 스트리밍 저장
	if os.system( rec_call.encode('utf-8') ) != 0 :
		logger.error( "Recoding_info : rec_call [%s]" % rec_call )
		return 100000
	logger.info( "Success Recoding. Start File move..." )


	#5. 파일 이동
	mv_call = "mv %s\"%s\" %s" % ( cfg_temp_dir , rec_flnm , cfg_target_dir )
	if os.system( mv_call.encode('utf-8') ) != 0 :
		logger.error( "Don't Move file. Call [%s]" % mv_call )
		return 200000
	logger.info( "Move Success.[%s/%s]" % ( rec_flnm , cfg_target_dir ) )
	logger.info( ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::" )
	time.sleep( 30 )
	return 0


if __name__ == "__main__":
	if len(sys.argv) > 2 :
		rec_stt_time = sys.argv[1]
		rec_end_time = sys.argv[2]
	else :
		rec_stt_time = cfg_stt_time
		rec_end_time = cfg_end_time

	# 로그 초기화
	logger = init_log(True,False)
	logger.info( "========================= Start =========================" )
	logger.info( "KBS Cool FM 891MHz Radio Streaming Recoder." )

	# 계속 녹화
	while rec_kbs_radio( rec_stt_time , rec_end_time ) >= 0 :
		# 시간 지정시 1회 실행
		if len(sys.argv) > 2 :
			break	# 계속 녹화

	logger.info( "=========================  End  =========================\n\n\n" )