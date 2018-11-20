#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
rec_dft_name = u'AKMU_Suhyun VolumeUp.mp4'
rec_bora_url = "http://myk.kbs.co.kr/live_popup?chid=25&chtype=RADIO"
#rec_bora_url = "http://myk.kbs.co.kr/live/radio/25"
#google_cloud_platform_api_key = 'AIzaSyBSNGg7aQt0o5q6GPKShP3gegoxzKiZjnA'
rec_stt_time = 195900
rec_end_time = 215700+3
rec_try_cnt  = 10
RTMP_INFO    = {
	'service_url': 'rtmp://live.kbskme.gscdn.com/bora_2fm/_definst_/bora_2fm_5.stream' ,
	'channel_code': '25' ,
	'channel_type': 'RADIO' ,
	'isPopup': 'true'
}
#######################################################################

# pip install module
import requests
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

if len(sys.argv) > 2 :
	pass
else :
	test =1 
	if test == 0 :
		#0. 보이는라디오 일정 확인
		dBora_schl = requests.get('http://kong.kbs.co.kr/bora_admin/boraradio/get_bora_schedule_JSON.php').json()
		lChannel   = dBora_schl['2FM']['PM']
		for i in range( len ( lChannel ) ) :
			if lChannel[i]['START_TIME'] == '20:00' :
				break
		nTodayWeek = ( datetime.datetime.today().weekday()+1 ) * 10
		if lChannel[i]['DAY_NUMBERS'].split(',').count( str(nTodayWeek) ) == 0 :
			logger.error( "Today is not a 'VisibleRadio' broadcast date. [%d]" % nTodayWeek )
			logger.error( "VisibleRadio Schedule                         [%s]" % lChannel[i]['DAY_NUMBERS'] )
			exit(-1)
	else :
		#0. 보이는라디오 정보 획득
		Chl_mtitle = ''
		Chl_stitle = ''
		Chl_person = ''
		Chl_story  = ''
		Chl_opn_yn = ''
				
#		dBora_schl = requests.get('http://myk.kbs.co.kr/broadcast_live/channel_master_items_json').json()
#		Chl_mtitle = dBora_schl['live_episode_items'][30]['now_schedule_item']['program_title']
#		Chl_opn_yn = dBora_schl['live_episode_items'][30]['now_schedule_item']['radio_open_studio_yn']
#		try :
#			Chl_stitle = dBora_schl['live_episode_items'][30]['now_schedule_item']['subtitle']
#		except :
#			pass
#		try:
#			Chl_person = dBora_schl['live_episode_items'][30]['now_schedule_item']['broadcast_persons_names']
#		except :
#			pass
#		try :
#			Chl_story  = dBora_schl['live_episode_items'][30]['now_schedule_item']['storyline']
#		except :
#			pass

#		dBora_schl = requests.get('http://myk.kbs.co.kr/broadcast/broadcast_episode_read').json()
#		Chl_mtitle = dBora_schl['program_title']
#		Chl_stitle = dBora_schl['subtitle']
#		Chl_person = dBora_schl['broadcast_persons_names']
#		Chl_story  = dBora_schl['storyline']
#		Chl_opn_yn = dBora_schl['radio_open_studio_yn']
#		
#		print Chl_mtitle.encode('utf-8')
#		print Chl_stitle.encode('utf-8')
#		print Chl_person.encode('utf-8')
#		print Chl_story .encode('utf-8')
#		print Chl_opn_yn.encode('utf-8')
#		exit (0)



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


	#1. 세션의 pk값 획득
	ses      = requests.Session()
	pk_req   = ses.get(rec_bora_url)
	pk_soup  = BeautifulSoup(pk_req.text, 'html.parser')
	pk_token = pk_soup.find("input" , { "name" : "pk_token" } )


	#2. pk값을 RTMP_INFO 딕셔너리에 추가
	RTMP_INFO['pk_token'] = pk_token['value']


	#3. RTMP 주소 획득
	bora_req = ses.post('http://myk.kbs.co.kr/api/kp_cms/live_stream', data=RTMP_INFO).json()


	#4. RTMP 저장
	rec_url  = bora_req[u'real_service_url']                                              # url
	rec_ddtm = bora_req[u'server_datetime'][2:8] + "_" + bora_req[u'server_datetime'][8:] # 날짜
	rec_flnm = rec_ddtm + " " + rec_dft_name
	rec_time = int((datetime.datetime.strptime(str(rec_end_time), '%H%M%S') - datetime.datetime.strptime(str(sTm), '%H%M%S' )).total_seconds())
	rec_call = ( "/opt/bin/rtmpdump -r \"%s\" -o \"/opt/usr/%s\" -v -B %d" ) % ( rec_url , rec_flnm , rec_time )
	logger.info( "Recoding_info : rec_url  [%s... ]" % rec_url[:55] )
	logger.info( "Recoding_info : rec_ddtm [%s]"     % rec_ddtm     )
	logger.info( "Recoding_info : rec_flnm [%s]"     % rec_flnm     )
	logger.info( "Recoding_info : rec_time [%d]"     % rec_time     )
	logger.info( "Start Recoding..." )
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