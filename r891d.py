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
2-1. 19.08.05 보라는 720p 30f(2시간 덤프시 약 2GB)로 저장된다.
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
from pytz     import timezone

DEF_C891D_URL = 'http://kbs-radio-891mhz-crawler.appspot.com'
DEF_VERSION   = 'v1.21.190814'

@atexit.register
def byebye() :
	logger.info( "===============================  End  ===============================\n\n" )
#	if os.name == 'nt' :
#		input()

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
		logger.setLevel(logging.DEBUG)
		logger.addHandler(log_scrn)
	return logger


def init_cfg( file ) :
	# 디폴트값
	dCfgJson = { 'CFG_PROGRAM_STIME' : '200000'
	           , 'CFG_REC_STT_TIME'  : '195920'
	           , 'CFG_REC_END_TIME'  : '215830'
	           , 'CFG_AUD_STT_TIME'  : '200000'
	           , 'CFG_AUD_END_TIME'  : '215830'
	           , 'CFG_TEMP_DIR'      : './'
	           , 'CFG_TARGET_DIR'    : './'
	           , 'CFG_DAEMON_YN'     : 'N'
	           , 'CFG_HB_MIN'        : 1
	           , 'CFG_REC_WATER_MK'  : ''
	           , 'CFG_AUD_WATER_MK'  : ''
#	           , 'CFG_YOUTUBE'       : { 'STITLE' : [ '[행복하오니]'
#	                                                , '[뭘 좋아할지 몰라서 주제를 정해봤어]'
#	                                                , '[TMI 퀴즈]'
#	                                                , '[200% 초대석]'
#	                                                , '[오늘은 왠지 하림과 낙타]'
#	                                                , '[스튜디오]'
#	                                                , '[주간볼륨]'
#	                                                ]
#	                                   , 'INFO'   : { 'title'                  : '악동뮤지션 수현의 볼륨을 높여요'
#	                                                , 'description'            : 'KBS Cool FM 89.1MHz 매일 20:00-22:00 볼륨을높여요#nDJ : #수현of악동뮤지션(AKMU SUHYUN)#n연출 : 정혜진, 윤일영 / 작가 : 김희진, 류민아#nHP : http://program.kbs.co.kr/2fm/radio/svolume#nIG : https://instagram.com/volumeup891#n#악동뮤지션수현의볼륨을높여요 #수현의볼륨을높여요 #kbsradio'
#	                                                , 'category'               : 'Entertainment'
#	                                                , 'tags'                   : '악동뮤지션, 수현, 이수현, 볼륨을 높여요, AKMU, SUHYUN, AKDONG MUSICIAN'
#	                                                , 'default-language'       : 'ko'
#	                                                , 'default-audio-language' : 'ko'
#	                                                , 'privacy'                : 'private'
#	                                                , 'client-secrets'         : '.client_secrets.json'
#	                                                , 'credentials-file'       : '.youtube-upload-credentials.json'
#	                                                }
#	                                   , 'UPLOAD_AUD' : 'unlisted'
#	                                   , 'UPLOAD_VID' : 'unlisted'
#	                                   }
	           }

	try: 
		with open( file , encoding='utf-8' ) as rfile:
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
	if bReady == False :
		# 파일 여부 확인
		sExecFlnm = 'ffmpeg' + ( '.exe' if ( os.name == 'nt' ) else ''  )
		sSplitCha =            ( ';'    if ( os.name == 'nt' ) else ':' )
		bExistFile = False

		for i in os.environ['PATH'].split( sSplitCha ) :
			bExistFile = ( bExistFile or os.path.isfile( os.path.join( i , sExecFlnm ) ) )
		if bExistFile == False :
			logger.error( "(%s)가 없습니다. (%s) 에서 다운받은 후 (%s)를 같은 폴더에 위치하세요." , sExecFlnm , 'https://www.ffmpeg.org' , sExecFlnm )
			return( [ -4 , "" ] )

	bora_html = requests.get( dCFG['DEF_C891D_URL'] , headers = {'User-Agent': 'r891d/'+dCFG['DEF_VERSION']})
	if bora_html.status_code != 200 :
		logger.error( "방송 정보를 가져오지 못했습니다." )
		return( [ -1 , "" ] )
	dRadio891Data = json.loads(bora_html.text)
	if int( dRadio891Data['result_no'] ) < 0 :
		logger.error( dRadio891Data['result_msg'] )
		return( [ -2 , "" ] )

	if bReady == False :
		logger.info( '-----Notice %s--------------------------------------------' , dRadio891Data['cache_ddtm'] )
		for i in range( len( dRadio891Data['info_msg'] ) )  :
			logger.info( dRadio891Data['info_msg'][i] )
		logger.info( '-----Start---End----Bora--Title--------------------------------------' )
	for i in range( len( dRadio891Data['schedule_table'] ) ):
		sTarget = ''
		if len(sys.argv) > 2 :
			dRadio891Data['strm_title'  ] = 'KBS Cool FM 89.1Mhz'
			dRadio891Data['strm_optn_yn'] = 'Y'
			if dRadio891Data['schedule_table'][i]['sTime'] < dCFG['CFG_REC_END_TIME'] and dRadio891Data['schedule_table'][i]['eTime'] > dCFG['CFG_REC_END_TIME']  :
				sTarget = '*'
		elif dRadio891Data['schedule_table'][i]['sTime'] == dCFG['CFG_PROGRAM_STIME'] :
			dRadio891Data['strm_title'  ] = dRadio891Data['schedule_table'][i]['title']
			dRadio891Data['strm_optn_yn'] = dRadio891Data['schedule_table'][i]['opnYn']
			#보라가 아닐 때 프로그램시작시각을 오디오 시작 시간으로 변경
			if dRadio891Data['strm_optn_yn'] == 'N' :
				dCFG['CFG_REC_STT_TIME'] = dCFG['CFG_AUD_STT_TIME']
				dCFG['CFG_REC_END_TIME'] = dCFG['CFG_AUD_END_TIME']
			sTarget = '*'
		if bReady == False :
			logger.info( "[%1s]  %s  %s   %s   %s" , sTarget , dRadio891Data['schedule_table'][i]['sTime'], dRadio891Data['schedule_table'][i]['eTime'] , dRadio891Data['schedule_table'][i]['opnYn'] , dRadio891Data['schedule_table'][i]['title'] )
	if bReady == False :
		logger.info ( "---------------------------------------------------------------------" )
		return( [ 0 , "" ] )

#	dRadio891Data['strm_optn_yn'  ] ='N'

	# 스트리밍 정보 설정
	sCurrentTime = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%H%M%S')
	strm_time    = ( datetime.datetime.strptime( dCFG['CFG_REC_END_TIME']  , '%H%M%S' ) - datetime.datetime.strptime( sCurrentTime , '%H%M%S' ) ).total_seconds() + ( 86400 if( dCFG['CFG_REC_END_TIME'] < sCurrentTime ) else 0 )
	dRadio891Data['strm_time'] = strm_time
	dRadio891Data['strm_ddtm'] = dRadio891Data['cache_ddtm'][:7] + sCurrentTime
	dRadio891Data['strm_flnm'] = dRadio891Data['strm_ddtm'] + " " + dRadio891Data[u'strm_title'] + ( ".H264" if( dRadio891Data['strm_optn_yn'] == 'Y') else "" ) + ".AAC.ts"
	dRadio891Data['strm_url' ] = ( dRadio891Data['strm_url_540p'] if( dRadio891Data['strm_optn_yn'] == 'Y') else dRadio891Data['strm_url_audio'] )

	if os.name == 'nt' and ( 'CFG_REC_WATER_MK' in dCFG or 'CFG_AUD_WATER_MK' in dCFG ):
		if dRadio891Data['strm_optn_yn'  ] == 'Y' :
			if dCFG['CFG_REC_WATER_MK'] != '' :
				sFfmpegOpt =                                                                                        "-c:a copy -b:v 2000k             -vf drawtext=text=\"%s\":fontcolor=white:fontfile=font.ttf:fontsize=16:box=1:boxcolor=black@0.5:boxborderw=5:x=w-text_w-20:y=h-text_h-20" % ( dCFG['CFG_REC_WATER_MK'] )
			else :
				sFfmpegOpt =                                                                                        "-c   copy                        "
		else :
			if dCFG['CFG_AUD_WATER_MK'] != '' and 'CFG_YOUTUBE' in dCFG:
#				sFfmpegOpt = "-loop 1 -framerate 1 -i cover.jpg -c:v libx264 -preset slow -tune stillimage -shortest -c:a copy -b:v  300k -s  640:360 -vf drawtext=text=\"%s\":fontcolor=white:fontfile=font.ttf:fontsize=32:box=1:boxcolor=black@0.5:boxborderw=5:x=w-text_w-20:y=h-text_h-20" % ( dCFG['CFG_AUD_WATER_MK'] )
				sFfmpegOpt = "-loop 1 -framerate 1 -i cover.jpg -c:v libx264 -preset slow -tune stillimage -shortest -c:a copy -b:v  300k -s  640:360 -vf drawbox=y=400:color=black@0.4:width=iw:height=80:t=fill,drawtext=text=\"%s\":fontcolor=white:fontfile=font.ttf:fontsize=52:x=(w-tw)/2:y=h-124" % ( dCFG['CFG_YOUTUBE']['STITLE'][datetime.datetime.now().weekday()].split(']')[1].strip() if( dCFG['CFG_AUD_WATER_MK'] == 'STITLE' ) else dCFG['CFG_AUD_WATER_MK'] )
			else :
				sFfmpegOpt = "-loop 1 -framerate 1 -i cover.jpg -c:v libx264 -preset slow -tune stillimage -shortest -c:a copy -b:v  300k -s  640:360"
	else :
		sFfmpegOpt = "-c copy"#-loglevel warning 

	dRadio891Data['strm_call'] = ( 'ffmpeg -i \"%s\" -y -t %d %s \"%s\"' ) % ( dRadio891Data['strm_url'] , strm_time , sFfmpegOpt , os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] ) )

	logger.debug( "Radio cache_ddtm     = [%s]"    , dRadio891Data['cache_ddtm'    ]      )#cache서버
	logger.debug( "Radio strm_url_audio = [%s...]" , dRadio891Data['strm_url_audio'][:40] )#cache서버
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
		( [ -1000 , "" ] )
	logger.info( "Success Dumped. And... " )


	# 스트리밍 파일 처리
	try :
		rtn_path = shutil.copy( os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] ) , dCFG['CFG_TARGET_DIR'] )
	except :
		rtn_path = os.path.join( dCFG['CFG_TEMP_DIR'] , dRadio891Data['strm_flnm'] )
	logger.info( "File [%s]" , rtn_path )

	return( [ 0 , rtn_path ] )


def Upload2Youtube( dYtb , sFile ) :
	oDdTmNow = datetime.datetime.now()
	nWeekday = (oDdTmNow).weekday()

	dYtb['INFO']['title'         ] = '%s %s %s' % ( sFile[2:8] , dYtb['INFO']['title'] , dYtb['STITLE'][nWeekday].split(']')[1].replace('#','') )
	dYtb['INFO']['description'   ] = '%s#n%s' % ( dYtb['STITLE'][nWeekday] , dYtb['INFO']['description'] )
	dYtb['INFO']['recording-date'] = (oDdTmNow).replace(microsecond=0).isoformat() + ".0Z"
#	dYtb['INFO']['publish-at'    ] = (oDdTmNow).replace(microsecond=0).isoformat() + ".0Z"
	if 'H264' in sFile :
		dYtb['INFO']['privacy'] = dCFG['CFG_YOUTUBE']['UPLOAD_VID']
	else :
		dYtb['INFO']['privacy'] = dCFG['CFG_YOUTUBE']['UPLOAD_AUD']
	
	sExe = os.path.join(os.path.dirname(os.path.realpath(__file__)),'youtube-upload')
	for sKey in dYtb['INFO'].keys() :
		sExe += " --%s=\"%s\"" % ( sKey , dYtb['INFO'][sKey] )
	sExe += " \"%s\"" % sFile

	logger.info( '---------------------------------------------------------------------' )

	nRtn = os.system( sExe )
	if nRtn != 0 :
		logger.error( "Upload Error[%d,%s]. " % ( nRtn , sExe ) )
	else :
		logger.info( "Upload Success[%d]. " % nRtn )
	return nRtn


if __name__ == "__main__":
	# 초기화 및 환경설정
	init_signal()
	logger = init_log(True,True) # 파일,화면
	dCFG   = init_cfg(os.path.splitext(sys.argv[0])[0] + '.json')

	logger.info( '=============================== Start ===============================' )
	logger.info( 'KBS Cool FM 89.1Mhz Streaming Dumper (%s)',dCFG['DEF_VERSION'] )

	# 방송정보 확인
	if GetInfoAndStartDump( dCFG , False )[0] < 0 :
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
		lRtn = GetInfoAndStartDump( dCFG , True )
		if lRtn[0] < 0 :
			continue

		# 녹화정보 업로드
		if 'CFG_YOUTUBE' in dCFG :
			Upload2Youtube( dCFG['CFG_YOUTUBE'] , lRtn[1] )

		if dCFG['CFG_DAEMON_YN'] not in ( 'Y',  'y' ) :
			break

		logger.info( 'Waits for the next dumping...' )
		time.sleep( dCFG['CFG_HB_MIN']*60 )
