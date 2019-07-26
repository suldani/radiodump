#!/usr/bin/env python
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------
#Radio crawler(ver.KBSFM0891)
#KBS라디오 정보를 저장한다.
#---------------------------------------------------------------------
#라이브러리 설치
# pip install requests bs4 pytz
#리눅스 실행
#1. 대몬 : nohup c891d.py >/dev/null 2>&1 &
#2. 1회  : c891d.py [ 시작시간[HHMMSS] 종료시간[HHMMSS] ]
#daemon설치방법
#1. /jffs/scripts/post-mount 파일에 아래 내용 추가
#        cru a "execute c891d" "50 19 * * * /opt/usr/c891d.py >/dev/null 2>&1"
#        cru a "kill    c891d" "49 19 * * * killall c891d"
#        /opt/usr/c891d.py >/dev/null 2>&1
#######################################################################
cfg_bora_url      = 'http://onair.kbs.co.kr/?sname=onair&stype=live&ch_code=25&ch_type=radioList'
cfg_waiting_min   = 60
#######################################################################
import os
import sys
import platform
import datetime
import time
import logging
import logging.handlers
import re
import json
import requests
from bs4      import BeautifulSoup
from pytz     import timezone


global rec891json
rec891json = {'cache_ddtm':'000000_000000'}


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


def get_pgm_info() :
	bora_html = requests.get(cfg_bora_url)
	if bora_html.status_code != 200 :
		logger.error( "(err:%d) 방송 정보를 가져오지 못했습니다.(%s)" , bora_html.status_code , cfg_bora_url )
		return(-1)
	bora_soup = BeautifulSoup(bora_html.text, 'html.parser')


	try :
		schl_rinf = re.findall(r'var next = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		schl_jinf = json.loads(schl_rinf.replace('\\"','\"').replace('\\\\u','\\u').replace(r'\/','/'))
		rec891PList = []
		logger.debug( "[No] PgmId------Bora--Stt-----End-----PgmNm--------------------------")
		for i in range( len( schl_jinf['data'] ) ) :
			schl_jinf['data'][i]['program_stime'] = ( "%06d" % (int( schl_jinf['data'][i]['program_stime'] ) % 240000) )
			schl_jinf['data'][i]['program_etime'] = ( "%06d" % (int( schl_jinf['data'][i]['program_etime'] ) % 240000) )
			nIdx = len( rec891PList )
			if nIdx > 0 and rec891PList[nIdx-1]['title'] == schl_jinf['data'][i]['program_title'] :
				rec891PList[nIdx-1]['eTime'] = schl_jinf['data'][i]['program_etime']
			else :
				rec891PList += [{'sTime' : schl_jinf['data'][i]['program_stime']
								,'eTime' : schl_jinf['data'][i]['program_etime']
								,'opnYn' : schl_jinf['data'][i]['radio_open_studio_yn']
								,'title' : schl_jinf['data'][i]['program_title']
								,'pcode' : schl_jinf['data'][i]['program_code']
								}]
		#리스트확인코드
		for i in range( len( rec891PList ) ):
			logger.info( "[%02d] %s   %s   %s  %s" % (i ,rec891PList[i]['sTime'], rec891PList[i]['eTime'], rec891PList[i]['opnYn'] , rec891PList[i]['title']))
	except :
		logger.error( "방송 정보 파싱중 실패했습니다." )
		return(-2)


	try :
		strm_rdat      = re.findall(r'var channel = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		strm_jdat      = json.loads(strm_rdat.replace('\\"','\"').replace('\\\\u','\\u').replace(r'\/','/'))

		cache_ddtm     = strm_jdat['cached_datetime'][2:10].replace('-','') + "_" + strm_jdat[u'cached_datetime'][11:].replace(':','')   # 날짜
		strm_url_audio = strm_jdat['channel_item'][0]['service_url']
		strm_url_540p  = strm_jdat['channel_item'][1]['service_url']
		strm_url_360p  = '' #strm_jdat['channel_item'][1]['service_url']
		#kong_html      = requests.get( strm_url_360p ) #기존 kong주소는 휴대폰 전용으로 바뀌어져 vbr로 송출되는것으로 추측
		#strm_url_540p  = "http://kong.kbskme.gscdn.com/smart_bora_2fm/_definst_/smart_bora_2fm_5.stream/" + kong_html.text.splitlines()[3]
	except :
		logger.error( "스트리밍 정보 파싱에서 실패했습니다." )
		return(-3)


	try :
		subtitle_rinf = re.findall(r'var channelinfoListJson.*({\\\\\\"program_ch_code\\\\\\":\\\\\\"25.*?ad_del_yn.*?\})', bora_soup.text)[0]
		subtitle_jinf = json.loads(subtitle_rinf.replace('\\\\\\"','\"').replace('\\\\\\\\u','\\u').replace('\\\\\\\\/','/'))

		dNow = { 'program_code'     : subtitle_jinf['program_code']
		       , 'program_title'    : subtitle_jinf['program_title']
		       , 'program_subtitle' : subtitle_jinf['program_subtitle']
		       , 'program_staff'    : subtitle_jinf['program_staff']
		       , 'program_homeurl'  : subtitle_jinf['program_homeurl']
		       , 'program_date'     : subtitle_jinf['program_date']
		       , 'open_studio_yn'   : subtitle_jinf['radio_open_studio_yn']
			   }
	except :
		dNow.clear()
		logger.error( "실시간 방송 정보 파싱중 실패했습니다." )


	rec891json = { 'cache_ddtm'     : cache_ddtm
	             , 'strm_url_audio' : strm_url_audio
	             , 'strm_url_360p'  : strm_url_360p
	             , 'strm_url_540p'  : strm_url_540p
				 , 'now'            : dNow
				 , 'schedule_table' : rec891PList
	             }

	with open('radio891.json', 'w') as outfile :
		json.dump(rec891json, outfile)

	return(0)


if __name__ == "__main__":
	# 로그 초기화
	logger = init_log(True,True)
	logger.info( "=============================== Start ===============================" )
	logger.info( "KBS Cool FM 89.1MHz Radio streaming crawler" )

	while True :
		nRtn = get_pgm_info()
		if nRtn < 0 :
			break
		logger.info( "%d 분 후 라디오 정보를 가져옵니다." , cfg_waiting_min )
		time.sleep( 60 * cfg_waiting_min )

	logger.info( "===============================  End  ===============================\n\n\n" )