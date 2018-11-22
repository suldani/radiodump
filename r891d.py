#!/opt/bin/python3
# -*- coding: utf-8 -*-
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
설명
KBS 라디오 89.1MHz 정보를 가져와 DirectScream으로 저장한다.
오픈스튜디오이면 mp4로 영상, 아니면 m4a로 오디오만 저장한다.
저장중 네트웍이상, 정전 등의 오류 발생시에는 바로 재실행한다.

참고
1. kbs측 스트리밍 데이터의 캐시(추정)로 일찍 덤프가 시작된다.
시간을 정확하게 맞추고 싶다면 덤프시간을 15~20초정도 앞당길것
2. 현재 보라는 540p 30f(2시간 덤프시 약 1GB)로 저장되나,
   종종 알 수 없는 이유 20f로 저장되는 경우가 있다.
3. 프로그램정보를 캐시서버에서 가져오기 때문에 KBS측의 부하는 없다.
4. 자정이 걸리는 시간은 오류 있음.
---------------------------------------------------------------------
리눅스 실행
1. 대몬 : nohup r891d.py >/dev/null 2>&1 &
2. 1회  : r891d.py [ 시작시간[HHMMSS] 종료시간[HHMMSS] ]
          옵션을 줄 시 무조건 오픈스튜디오로 저장된다.

daemon설치방법
1. /jffs/scripts/post-mount 파일에 아래 내용 추가
        cru a "execute r891d" "50 19 * * * /opt/home/r891d.py >/dev/null 2>&1"
        cru a "kill    r891d" "49 19 * * * killall python"
        /opt/home/r891d.py >/dev/null 2>&1
2. /jffs/scripts/unmount 파일에 아래 내용 추가
        killall python
3. reboot 후 ps | grep r891d 실행중인지 확인한다.
---------------------------------------------------------------------
pip install requests pytz
pip install pyinstaller / pyinstaller --i=coolfm.ico -F r891d.py
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
import json
import datetime
import time
import os
import sys
import shutil
import atexit
import signal
import logging
import logging.handlers

# pip install requests pytz
import requests
from pytz     import timezone

DEF_C891D_URL = 'https://kbs-radio-891mhz-crawler.appspot.com'
DEF_VERSION   = 'v0.99.181122'

@atexit.register
def byebye() :
	logger.info( "===============================  End  ===============================\n\n" )

def sigHandler(signum,f) :
	SIGNALS_TO_NAMES_DICT = dict((getattr(signal, n), n) for n in dir(signal) if n.startswith('SIG') and '_' not in n )
	logger.info( "(%02d:%s) Bye-bye." , signum , SIGNALS_TO_NAMES_DICT[signum] )
	sys.exit( 0 )

def init_signal() :
	for x in dir(signal):
		if x in ('SIGTERM' , 'SIGINT' ) :
			signum = getattr(signal, x)
			signal.signal(signum, sigHandler)


def init_log(bFile,bScrn) :
	# 로거 생성
	logger = logging.getLogger('main')

	if bFile and os.name == 'posix':
		# 파일 핸들러 생성
		log_file  = logging.handlers.RotatingFileHandler( filename=sys.argv[0][:-2]+'log' , maxBytes=(100*1024) ) #100KB, 1회
		log_file.setFormatter( logging.Formatter('%(asctime)s [%(lineno)03d:%(levelname)7s] %(message)s') )
		logger.setLevel(logging.DEBUG)
		logger.addHandler(log_file)
	if bScrn :
		log_scrn  = logging.StreamHandler()
		log_scrn.setFormatter( logging.Formatter('%(message)s') )
		logger.setLevel(logging.INFO)
		logger.addHandler(log_scrn)
	return logger


def init_cfg( file ) :
	# 디폴트값
	dCfgJson = { 'CFG_PROGRAM_STIME' : '200000'
	           , 'CFG_REC_STT_TIME'  : '195520'
	           , 'CFG_REC_END_TIME'  : '215800'
	           , 'CFG_TEMP_DIR'      : './'
	           , 'CFG_TARGET_DIR'    : './'
	           , 'CFG_DAEMON_YN'     : 'N'
	           , 'CFG_HB_MIN'        : 1
	           }

	try :
		with open( file ) as rfile:
			dCfgJson = json.load(rfile)
			logger.info( "Load config file.(%s)" , file )
	except :
		with open( file , 'w') as wfile :
			json.dump(dCfgJson, wfile)
			logger.info( "Default config file.(%s)" , file )

	dCfgJson['DEF_C891D_URL'] = DEF_C891D_URL
	dCfgJson['DEF_VERSION'  ] = DEF_VERSION

	if len(sys.argv) > 2 :
		dCfgJson['CFG_REC_STT_TIME'] = sys.argv[1]
		dCfgJson['CFG_REC_END_TIME'] = sys.argv[2]

	return dCfgJson


def WaitingForDump( sRecSttTime , sRecEndTime ):
	sCurrentTime = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%H%M%S')
	if  ( int(sRecSttTime) >  int(sRecEndTime) and not ( int(sCurrentTime) >= int(sRecEndTime) and int(sCurrentTime) < int(sRecSttTime) ) ) \
		or ( int(sRecSttTime) <= int(sRecEndTime) and not ( int(sCurrentTime) >= int(sRecEndTime) or  int(sCurrentTime) < int(sRecSttTime) ) ) :
		nSleepTime = 0
	else :
		nSleepTime = int(( datetime.datetime.strptime( sRecSttTime , '%H%M%S' )
						- datetime.datetime.strptime( sCurrentTime , '%H%M%S' )
						).total_seconds()
						)
		nSleepTime = nSleepTime + ( 0 if( nSleepTime >= 0 ) else 86400 )
	return { 'nSleepTime' : nSleepTime , 'sCurrentTime' : sCurrentTime }


def GetInfoAndStartDump( dCFG , bReady ) :
	bora_html = requests.get( dCFG['DEF_C891D_URL'] , headers = {'User-Agent': 'r891d/'+dCFG['DEF_VERSION']})
	if bora_html.status_code != 200 :
		logger.error( "방송 정보를 가져오지 못했습니다." )
		return( -1 )
	dRadio891Data = json.loads(bora_html.text)
	if int( dRadio891Data['result_no'] ) < 0 :
		logger.error( dRadio891Data['result_msg'] )
		return( -2 )

	if bReady == False :
		logger.info( '-----Notice %s--------------------------------------------' , dRadio891Data['cache_ddtm'] )
		for i in range( len( dRadio891Data['info_msg'] ) )  :
			logger.info( dRadio891Data['info_msg'][i] )
		logger.info( '-----Start---End----Bora--Title--------------------------------------' )
	for i in range( len( dRadio891Data['schedule_table'] ) ):
		sTarget = ''
		if len(sys.argv) > 2 :
			dRadio891Data['strm_title'  ] = 'KBS 89.1Mhz CoolFM Radio'
			dRadio891Data['strm_optn_yn'] = 'Y'
			if dRadio891Data['schedule_table'][i]['sTime'] < dCFG['CFG_REC_END_TIME'] and dRadio891Data['schedule_table'][i]['eTime'] > dCFG['CFG_REC_END_TIME']  :
				sTarget = '*'
		elif dRadio891Data['schedule_table'][i]['sTime'] == dCFG['CFG_PROGRAM_STIME'] :
			dRadio891Data['strm_title'  ] = dRadio891Data['schedule_table'][i]['title']
			dRadio891Data['strm_optn_yn'] = dRadio891Data['schedule_table'][i]['opnYn']
			sTarget = '*'
		if bReady == False :
			logger.info( "[%1s]  %s  %s   %s   %s" , sTarget , dRadio891Data['schedule_table'][i]['sTime'], dRadio891Data['schedule_table'][i]['eTime'] , dRadio891Data['schedule_table'][i]['opnYn'] , dRadio891Data['schedule_table'][i]['title'] )
	if bReady == False :
		logger.info ( "---------------------------------------------------------------------" )
		return( 0 )


	# 스트리밍 정보 설정
	sCurrentTime = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%H%M%S')
	strm_time    = ( datetime.datetime.strptime( dCFG['CFG_REC_END_TIME']  , '%H%M%S' ) - datetime.datetime.strptime( sCurrentTime , '%H%M%S' ) ).total_seconds() + ( 86400 if( dCFG['CFG_REC_END_TIME'] < sCurrentTime ) else 0 )
	dRadio891Data['strm_time'] = strm_time
	dRadio891Data['strm_ddtm'] = dRadio891Data['cache_ddtm'][:7] + sCurrentTime
	dRadio891Data['strm_flnm'] = dRadio891Data['strm_ddtm'] + " " + dRadio891Data[u'strm_title'] + ( ".mp4" if( dRadio891Data['strm_optn_yn'] == 'Y') else ".m4a" )
	dRadio891Data['strm_url' ] = ( dRadio891Data['strm_url_540p'] if( dRadio891Data['strm_optn_yn'] == 'Y') else dRadio891Data['strm_url_audio'] )
	dRadio891Data['strm_call'] = ( 'ffmpeg -i \"%s\" -y  -loglevel warning -t %d -c copy \"%s\"' ) % ( dRadio891Data['strm_url'] , strm_time , os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] ) ) #  -loglevel warning

	logger.debug( "Radio cache_ddtm     = [%s]"    , dRadio891Data['cache_ddtm'    ]      )#cache서버
	logger.debug( "Radio strm_url_audio = [%s...]" , dRadio891Data['strm_url_audio'][:40] )#cache서버
	logger.debug( "Radio strm_url_360p  = [%s...]" , dRadio891Data['strm_url_360p' ][:40] )#cache서버
	logger.debug( "Radio strm_url_540p  = [%s...]" , dRadio891Data['strm_url_540p' ][:40] )#cache서버
	logger.debug( "Radio strm_call      = [%s]"    , dRadio891Data['strm_call'     ]      )#추가된json
	logger.info ( "Radio strm_title     = [%s]"    , dRadio891Data['strm_title'    ]      )#cache서버
	logger.info ( "Radio strm_optn_yn   = [%s]"    , dRadio891Data['strm_optn_yn'  ]      )#cache서버

	logger.info ( "Radio strm_flnm      = [%s]"    , dRadio891Data['strm_flnm'     ]      )#추가된json
#	logger.debug( "Radio strm_ddtm      = [%s]"    , dRadio891Data['strm_ddtm'     ]      )#임시사용
#	logger.debug( "Radio strm_url       = [%s]"    , dRadio891Data['strm_url'      ]      )#임시사용
	logger.info ( "Radio strm_time      = [%d] (%02d:%02d:%02d)" % (strm_time, strm_time/3600, strm_time%3600/60 ,strm_time%60) )
	logger.info ( "---------------------------------------------------------------------")


	# 스트리밍 저장
	logger.info( "Start Dumping. If you want to stop, press [q]..." )
	if os.system( dRadio891Data['strm_call'] ) != 0 :
		logger.error( "Radio strm_call       = [%s]" % dRadio891Data['strm_call'] )
		return( -1000 )
	logger.info( "Success Dumped. And... " )


	# 스트리밍 파일 처리
	try :
		rtn_path = shutil.move( os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] ) , dCFG['CFG_TARGET_DIR'] )
	except :
		rtn_path = os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] )
	logger.info( "File [%s]" , rtn_path )

	return 0


if __name__ == "__main__":
	# 초기화 및 환경설정
	init_signal()
	logger = init_log(True,True) # 파일,화면
	dCFG   = init_cfg(os.path.splitext(sys.argv[0])[0] + '.json')

	logger.info( '=============================== Start ===============================' )
	logger.info( 'KBS Radio Cool FM 89.1MHz Streaming Dumper (%s)',dCFG['DEF_VERSION'] )

	# 방송정보 확인
	if GetInfoAndStartDump( dCFG , False ) < 0 :
		sys.exit(-1)

	# 계속 덤프
	while True :
		# 덤프까지 대기
		dWRtn = WaitingForDump( dCFG['CFG_REC_STT_TIME'] , dCFG['CFG_REC_END_TIME'] )
		if dWRtn['nSleepTime'] > 0 :
			logger.info( "Waiting [%5d] seconds... ( Start[%6s] End[%6s] Now[%6s] )" , dWRtn['nSleepTime'] , dCFG['CFG_REC_STT_TIME'] , dCFG['CFG_REC_END_TIME'] , dWRtn['sCurrentTime'] )
			time.sleep( dCFG['CFG_HB_MIN']*60 if( dWRtn['nSleepTime'] > dCFG['CFG_HB_MIN']*60 ) else dWRtn['nSleepTime'] )
			continue

		# 방송정보 확인 및 덤프 진행
		if GetInfoAndStartDump( dCFG , True ) < 0 :
			continue

		if dCFG['CFG_DAEMON_YN'] in ( 'N',  'n' ) :
			break

		logger.info( 'Waits for the next dumping...' )
		time.sleep( dCFG['CFG_HB_MIN']*60 )