#!/usr/bin/python3
# -*- coding: utf-8 -*-
# [START gae_python37_app]
#---------------------------------------------------------------------
#Radio crawler(ver.KBSFM0891)
#KBS라디오 정보를 저장한다.
#---------------------------------------------------------------------
#라이브러리 설치
# pip install -t lib/ requests bs4 pytz
# pip install -t lib/ -r requirements.txt
# virtualenv --python python3     ~/envs/hello_world
# source     ~/envs/hello_world/bin/activate
# gcloud app create
# gcloud app deploy app.yaml --project  kbs-radio-891mhz-crawler
#######################################################################
cfg_bora_url = 'http://onair.kbs.co.kr/?sname=onair&stype=live&ch_code=25&ch_type=radioList'
info_msg     = ['I expect AKMU to comeback this fall.'
               ,'Updated 2019.07.26:get more infomation...'
               ,'Updated 2019.02.14:KBS\'s streaming format is changed.'
               ]
#######################################################################
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
import time
import datetime
import re
import json
import requests
from bs4   import BeautifulSoup
from flask import Flask
from pytz  import timezone

# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)

global rec891json
rec891json = {'cache_ddtm':'000000_000000'}


@app.route('/')
def get_pgm_info() :
	global rec891json

	sDdTm = datetime.datetime.now(timezone('Asia/Seoul')).strftime('%y%m%d_%H%M%S')
	if rec891json['cache_ddtm'][:9] == sDdTm[:9] :
		print( '캐시된 정보를 사용합니다. 현재(%s) 기존(%s)' , rec891json['cache_ddtm'] , sDdTm )
		return app.response_class( response=json.dumps(rec891json,sort_keys=True ),	status=200,	mimetype='application/json'	)

	print( '정보를 수신 시도합니다. 현재(%s) 기존(%s)' , rec891json['cache_ddtm'] , sDdTm )
	rec891json.clear()
	rec891json['result'        ] = ''
	rec891json['result_msg'    ] = ''
	rec891json['info_msg'      ] = ''
	rec891json['cache_ddtm'    ] = ''
	rec891json['strm_url_audio'] = ''
	rec891json['strm_url_360p' ] = ''
	rec891json['strm_url_540p' ] = ''
	rec891json['schedule_table'] = ''

	try :
		bora_html = requests.get(cfg_bora_url)
		bora_soup = BeautifulSoup(bora_html.text, 'html.parser')
	except :
		rec891json['result_no'     ] = '-1'
		rec891json['result_msg'    ] = '방송 정보를 가져오지 못했습니다.'
		print( "%s %s" % ( rec891json['result_no'] , rec891json['result_msg'] ) )
		return app.response_class( response=json.dumps(rec891json),	status=200,	mimetype='application/json'	)

	try :
		schl_rinf = re.findall(r'var next = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		schl_jinf = json.loads(schl_rinf.replace('\\"','\"').replace('\\\\u','\\u').replace(r'\/','/'))
		rec891PList = []
		#print( "[No] PgmId------Bora--Stt-----End-----PgmNm--------------------------")
		for i in range( len( schl_jinf['data'] ) ):
			#print( "[%02d] %s   %s   %s  %s  %s" % (i ,schl_jinf['data'][i]['program_code'], schl_jinf['data'][i]['radio_open_studio_yn'], schl_jinf['data'][i]['program_stime'], schl_jinf['data'][i]['program_etime'] , schl_jinf['data'][i]['program_title']))
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
		#for i in range( len( rec891PList ) ):
		#	print( "[%02d] %s   %s   %s  %s" % (i ,rec891PList[i]['sTime'], rec891PList[i]['eTime'], rec891PList[i]['opnYn'] , rec891PList[i]['title']))

	except :
		rec891json['result_no'     ] = '-2'
		rec891json['result_msg'    ] = '방송 정보 파싱중 실패했습니다.'
		print( "%s %s" % ( rec891json['result_no'] , rec891json['result_msg'] ) )
		return app.response_class( response=json.dumps(rec891json),	status=200,	mimetype='application/json'	)


	try :
		strm_rdat      = re.findall(r'var channel = JSON\.parse\(\'(.*)\'\);', bora_soup.text)[0]
		strm_jdat      = json.loads(strm_rdat.replace('\\"','\"').replace('\\\\u','\\u').replace(r'\/','/'))

		cache_ddtm     = strm_jdat['cached_datetime'][2:10].replace('-','') + "_" + strm_jdat['cached_datetime'][11:].replace(':','')   # 날짜
		strm_url_audio = strm_jdat['channel_item'][0]['service_url']
		strm_url_540p  = strm_jdat['channel_item'][1]['service_url']
		strm_url_360p  = '' #strm_jdat['channel_item'][1]['service_url']
		#kong_html      = requests.get( strm_url_360p ) #기존 kong주소는 휴대폰 전용으로 바뀌어져 vbr로 송출되는것으로 추측
		#strm_url_540p  = "http://kong.kbskme.gscdn.com/smart_bora_2fm/_definst_/smart_bora_2fm_5.stream/" + kong_html.text.splitlines()[3]
	except :
		rec891json['result_no'     ] = '-3'
		rec891json['result_msg'    ] = '스트리밍 정보 파싱에서 실패했습니다.'
		print( "%s %s" % ( rec891json['result_no'] , rec891json['result_msg'] ) )
		return app.response_class( response=json.dumps(sorted(rec891json)),	status=200,	mimetype='application/json'	)


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
		print( '실시간 방송 정보 파싱중 실패했습니다.' )
		dNow.clear()

	rec891json = { 'result_no'      : '0'
				 , 'result_msg'     : 'OK'
				 , 'info_msg'       : info_msg
				 , 'cache_ddtm'     : cache_ddtm
				 , 'strm_url_audio' : strm_url_audio
				 , 'strm_url_360p'  : strm_url_360p
				 , 'strm_url_540p'  : strm_url_540p
				 , 'now'            : dNow
				 , 'schedule_table' : rec891PList
				 }

	return app.response_class( response=json.dumps(rec891json,sort_keys=True ),	status=200,	mimetype='application/json'	)


if __name__ == "__main__":
	print( "=============================== Start ===============================" )
	app.run(host='127.0.0.1', port=8080, debug=True)
	print( "===============================  End  ===============================" )

# [END gae_python37_app]