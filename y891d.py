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
pip install --upgrade google-api-python-client oauth2client progressbar2
pip install pyinstaller / pyinstaller --i=res\coolfm.ico -F r891d.py
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
from pytz           import timezone
from youtube_upload import main    

DEF_C891D_URL = 'http://kbs-radio-891mhz-crawler.appspot.com'
DEF_VERSION   = 'v1.10.190718'

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

	if bFile :
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
	           , 'CFG_UPLOAD_YN'     : 'N'
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

	return dCfgJson


def UploadFile( dCFG , sFile ) :
	dArgs = {}
	dArgs['title'                 ] = sFile[2:8] + " 악동뮤지션 수현의 볼륨을 높여요"
	dArgs['description'           ] = "KBS Cool FM 89.1MHz 매일 20:00-22:00 #볼륨을높여요#n#nDJ : #수현of악동뮤지션#n연출 : 정혜진, 윤일영#n작가 : 김희진, 류민아#nhttp://program.kbs.co.kr/2fm/radio/svolume#n#n*FAN_UPLOAD_UNOFFICIAL"
	dArgs['category'              ] = "People & Blogs"
	dArgs['tags'                  ] = "악동뮤지션, 수현, 이수현, 볼륨을 높여요"
	dArgs['default-language'      ] = "ko"
	dArgs['default-audio-language'] = "ko"
	dArgs['recording-date'        ] = datetime.datetime.now().replace(microsecond=0).isoformat() + ".0Z"
#	dArgs['publish-at'            ] = datetime.datetime.now().replace(microsecond=0).isoformat() + ".0Z"
	dArgs['privacy'               ] = "private"
	dArgs['client-secrets'        ] = ".client_secrets.json"
	dArgs['credentials-file'      ] = ".youtube-upload-credentials.json"

	sExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),'youtube_upload.bat')
	for sKey in dArgs.keys() :
		sExe += " --%s=\"%s\"" % ( sKey , dArgs[sKey] )
	sExe += " \"%s\"" % sFile

	logger.debug( sExe )
	logger.info( '---------------------------------------------------------------------' )

	nRtn = os.system( sExe )
	if nRtn != 0 :
		logger.info( "Upload Error[%d]. " % nRtn )
	else :
		logger.info( "Upload Success[%d]. " % nRtn )


if __name__ == "__main__":
	# 초기화 및 환경설정
	init_signal()
	logger = init_log(True,True) # 파일,화면
	dCFG   = init_cfg(os.path.splitext(sys.argv[0])[0] + '.json')

	logger.info( '=============================== Start ===============================' )
	logger.info( 'Youtube Uploader_%s  (KBS Radio Cool FM 89.1MHz)',dCFG['DEF_VERSION'] )

	UploadFile( dCFG , "d:\\Documents\\radiodump\\a.mp4" )
