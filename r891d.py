#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
rec_dft_name = u'[F]AKMU_Suhyun VolumeUp'
rec_bora_url = "http://onair.kbs.co.kr/index.html?sname=onair&stype=live&ch_code=25&ch_type=radioList&openradio=on"
rec_stt_time = 195700
rec_end_time = 215700+1
rec_try_cnt  = 10
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
from bs4      import BeautifulSoup
from pytz     import timezone

# 로거 생성
logger = logging.getLogger('main')
logger.setLevel(logging.DEBUG)

# 파일 핸들러 생성
log_file  = logging.FileHandler( sys.argv[0][:-2] + 'log' )
log_scrn  = logging.StreamHandler()

# 포멧터 생성 & 핸들러에 등록
formatter = logging.Formatter('%(asctime)s [%(lineno)03d:%(levelname)7s] %(message)s ')
log_file.setFormatter(formatter)
log_scrn.setFormatter(formatter)

# 핸들러를 로거에 등록, 다수의 핸들러를 등록할 수 있다.
logger.addHandler(log_file)
logger.addHandler(log_scrn)

nRecCnt = 0

# 볼륨시각
if len(sys.argv) > 2 :
	rec_stt_time = int( sys.argv[1] )
	rec_end_time = int( sys.argv[2] )

logger.info( "" )
logger.info( "" )
logger.info( "" )
logger.info( "=========================== Start ===========================" )
logger.info( "KBS Cool FM 891MHz Visual Radio Recoder." )
logger.info( "  rec_stt_time [%d]" % rec_stt_time )
logger.info( "  rec_end_time [%d]" % rec_end_time )

while True :
	#0. 공유기 py시각과 cron(sh)시각의 보정
	sTm = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%H%M%S')
	nNow = int( sTm )
	logger.info( "  Now......... [%d]" % nNow        )

	#0. 예외처리(방송시간 후인 경우 종료)
	if nNow >= rec_end_time :
		logger.warning( "Recording has ended. rec_end_time[%06d] nNow[%06d]" % ( rec_end_time , nNow ) )
		break

	#0. 예외처리(방송시간 전일 때 30초 간격으로 대기)
	if nNow < rec_stt_time :
		logger.warning( "The time is not broadcasting. Try again in 30 seconds. rec_end_time[%06d] nNow[%06d]" % ( rec_stt_time , nNow ) )
		time.sleep( 30 )
		continue

	#0. 예외처리(방송에서 오류가 생길시 30초 지연, 10회 이상시 프로그램 종료)
	if nRecCnt > 0 :
		if nRecCnt < rec_try_cnt :
			logger.warning( "An error occurred while recording. Try again in 30 seconds. cnt(%d/%d) nNow[%06d]" % (nRecCnt + 1, rec_try_cnt , nNow ) )
			time.sleep( 30 )
		else :
			logger.error( "The recording stops because of a large number of errors. cnt(%d/%d) nNow[%06d]" % (nRecCnt + 1, rec_try_cnt , nNow ) )
			break
	nRecCnt += 1


	#1. KBS CoolFM 원천정보 획득
	bora_html = requests.get(rec_bora_url)
	bora_soup = BeautifulSoup(bora_html.text, 'html.parser')


	#2. 원천정보 크래핑/가공하여 라디오 기초정보 설정
	bora_data = re.findall(r'var channel = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
	bora_req  = json.loads(bora_data.replace('\\',''))


	#3. 라디오or보라별 스트리밍 정보 설정
	openstudio_yn = 1
	rec_url  = bora_req['channel_item'][openstudio_yn]['service_url']                                                        # 보라url
	rec_ddtm = bora_req['cached_datetime'][2:10].replace('-','') + "_" + bora_req[u'cached_datetime'][11:].replace(':','')   # 날짜
	rec_flnm = rec_ddtm + " " + rec_dft_name + (".mp4" if ( openstudio_yn == 1 ) else ".m4a")                                # 파일명
	rec_time = int((datetime.datetime.strptime(str(rec_end_time), '%H%M%S') - datetime.datetime.strptime(str(sTm), '%H%M%S' )).total_seconds())
	rec_call = ( "/opt/bin/ffmpeg -i \"%s\" -y -t %d -c copy \"/opt/usr/%s\"" ) % ( rec_url , rec_time , rec_flnm )
	logger.info( "Recoding_info : rec_url  [%s... ]" % rec_url[:55] )
	logger.info( "Recoding_info : rec_ddtm [%s]"     % rec_ddtm     )
	logger.info( "Recoding_info : rec_flnm [%s]"     % rec_flnm     )
	logger.info( "Recoding_info : rec_time [%s]"     % rec_time     )
	logger.info( "Start Recoding..." )
	print rec_call


	#4. 스트리밍 저장
	if os.system( rec_call.encode('utf-8') ) != 0 :
		logger.error( "Recoding_info : rec_call [%s]" % rec_call )
		continue

	logger.info( "Success Recoding. Start File move..." )


	#5. 파일 이동
	mv_call = "mv \"/opt/usr/%s\" /mnt/WD8TB/_AKMU/6-2.RadioDJ_VolumeUp" % ( rec_flnm )
	if os.system( mv_call.encode('utf-8') ) == 0 :
		logger.info( "Move Success.[/mnt/WD8TB/_AKMU/6-2.RadioDJ_VolumeUp/%s]" % ( rec_flnm ) )
	else :
		logger.error( "Don't Move file. Call [%s]" % mv_call )
	break

logger.info( "===========================  End  ===========================" )