from flask import jsonify, render_template, request, send_file
import urllib
import urllib2
import base64
import StringIO
import json
import datetime

from maraschino import app
from maraschino.tools import *
import maraschino

#getting http/s setting from Maraschino
def sonarr_http():
    if get_setting_value('sonarr_https') == '1':
        return 'https://'
    else:
        return 'http://'

#creates url out of the ip
def sonarr_url(params = None):
    port = get_setting_value('sonarr_port')
    url_base = get_setting_value('sonarr_ip')
    webroot = get_setting_value('sonarr_webroot')

    if port:
        url_base = '%s:%s' % (url_base, port) 
    elif webroot:
        url_base = '%s/%s' % (url_base, webroot)
    url = url_base
    return sonarr_http() + url

#returns just the port or webroot
def sonarr_port():
    port = get_setting_value('sonarr_port')
    webroot = get_setting_value('sonarr_webroot')
    if port:
        return port
    elif webroot:
        return webroot

#returns the status of webroot so we can ensure we format the url string correctly
def sonarr_webroot_status():
    port = get_setting_value('sonarr_port')
    webroot = get_setting_value('sonarr_webroot')
    if port:
        return 0
    elif webroot:
        return 1

#to connect to Sonarr
def sonarr_api(params = None):
    api = get_setting_value('sonarr_api')
    url = sonarr_url() + params
    r = urllib2.Request(url)
    r.add_header("X-Api-Key", api)
    r = urllib2.urlopen(r).read()
    return json.JSONDecoder().decode(r)

#exception logging    
def log_exception(e):
    logger.log('Sonarr :: EXCEPTION -- %s' % e, 'DEBUG')

''' #Gets the episode overview: Currently unused
def get_episode_overview(params = None):
    params = '/api/episode/' + str(params)
    episodeoverview = sonarr_api(params=params)
    return episodeoverview['overview'] '''

def run_command(data = None):
    url = '/api/command/'
    api = get_setting_value('sonarr_api')
    url = sonarr_url() + url
    header = {'X-Api-Key': api}
    r = urllib2.Request(url, data, header)
    if str(urllib2.urlopen(r).read()):
        return True
    else:
        return False
    
#searches for a given episode    
def search_episode(params = None):
    ids = params
    data=json.dumps({'name':'episodesearch', 'episodeIds':[ids]})
    if run_command(data=data) == True:
        return True
    else:
        return False
    
'''calls for the above function, returning True or False depending on whether the search was able to complete
I've yet to find a way to see if the episode was found, but if I come accross a way, I'll update this to reflect that'''
@app.route('/xhr/sonarr/search_ep/<id>/')
def search_episodes(id):
    if search_episode(params=id) == True:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})


#main page
@requires_auth
@app.route('/xhr/sonarr/')
def xhr_sonarr_getshows():
    url = sonarr_api(params='/api/series')
    json_string = url   #opens previous json
    series = {}            #creates a list
    var1 = 0            #sets var1 up to be incremented
    for increment in json_string:   #just here to drop us down a level in the json
        try:            #catches the final error
            series.update({json_string[var1]['title']:[json_string[var1]['id'], json_string[var1]['titleSlug'], json_string[var1]['tvdbId']]}) #sets a variable to a dict of the id/titleslug
            var1 += 1           #increments var1 so we can move to the next entry in the json
        except:                 #error catching
            break               #breaks the loop when it hits an error
    
    images = series
    imagelist = sorted(series, key=lambda s: s.lower())
    return render_template('sonarr.html',
        lan = get_setting_value('sonarr_lan'),
        webroot = str(sonarr_webroot_status()),
        external_server = get_setting_value('sonarr_external_server'),
        port = sonarr_port(),
        url = get_setting_value('sonarr_ip'),
        http = sonarr_http(),
        images = images,
        imagelist = imagelist
        
    ) #renders the result to maraschino

#makes the search function of Sonarr available
@requires_auth   
@app.route('/xhr/sonarr/search')
def sonarr_search(message=None, params = None):
    sonarr = {}
    
    try:
        query = request.args['name']
        params = '/api/Series/lookup/?term=' + urllib.quote(query)
        print params
    except:
        pass
        
    try:
        sonarr = sonarr_api(params=params)
        amount = len(sonarr)
        sonarr = sonarr
        logger.log('Sonarr :: found %i series matching %s' % (amount, query), 'INFO')
        if amount != 0:
            try:
                var = 0
                series_list = []
                for increment in sonarr:
                    try:
                        titles = []
                        series_title = sonarr[var]['title']
                        series_tvdbid = sonarr[var]['tvdbId']
                        series_titleslug = sonarr[var]['titleSlug']
                        series_seasons = sonarr[var]['seasons']
                        try:
                            poster = sonarr[var]['remotePoster']
                        except:
                            poster = sonarr_url() + '/Content/Images/poster-dark.png'
                            print poster
                        try:
                            overview = sonarr[var]['overview']
                        except:
                            overview = ''
                        overview = (overview[:500] + '..') if len(overview) > 500 else overview
                        overview = (overview) if len(overview) != 0 else 'No description available for this show.'
                        titles.append(series_title)
                        titles.append(series_tvdbid)
                        titles.append(series_titleslug)
                        titles.append(series_seasons)
                        titles.append(poster)
                        titles.append(overview)
                        series_list.append(titles)
                        var += 1
                    except:
                        break
               
                params = '/api/profile'    
                profile_list = sonarr_api(params=params)
                var = 0
                profiles = {}
                profile_list = profile_list
                for incrementing in profile_list:
                    try:
                        profiles.update({profile_list[var]['id']:profile_list[var]['name']})
                        var += 1
                    except:
                        break
                        
                params = '/api/Rootfolder'
                folders = {}
                folder_list = sonarr_api(params=params)
                folder_list = folder_list
                var = 0
                for incrementing in folder_list:
                    try:
                        folders.update({folder_list[var]['path']:(round(float(folder_list[var]['freeSpace']) / (1000000000)))})
                        var += 1
                    except:
                        break
            except:
                log_exception(e)
        else:
            return render_template('sonarr/search.html', error='No series with "%s" were found' % (query), sonarr='results')
               
    except Exception as e:
        log_exception(e)
        sonarr = None
                
    else:
        logger.log('Sonarr :: Loading search template', 'DEBUG')
        sonarr = None
       
    return render_template('sonarr/search.html',
        webroot = str(sonarr_webroot_status()),
        titles = series_list,
        profiles = profiles,
        folders = folders,
        http = sonarr_http(),
        url = get_setting_value('sonarr_ip'),
        port = sonarr_port(),
        external_server = get_setting_value('sonarr_external_server'),
        lan = get_setting_value('sonarr_lan'),
        error = message
    )

#Allows you to add shows you find when searching. Currently sets all seasons to monitored, will look into adding a select box to give the option of only monitoring a few episodes
@app.route('/xhr/sonarr/add_show/<tvdbid>/<title>/<qualityprofile>/<seriestype>/<path>/<titleslug>/')
def add_series(tvdbid, title, qualityprofile, seriestype, path, titleslug):
    params = '/api/Series/lookup/?term=tvdbid:'+tvdbid
    season = sonarr_api(params=params)
    season = season[0]['seasons']
    
    try:
        logger.log('Sonarr :: Adding %s to library' % (title), 'INFO')
        title = str(title)
        tvdbId = str(tvdbid)
        qualityprofile = str(qualityprofile)
        seriestype = str(seriestype)
        path = str((urllib2.unquote(path)))
        titleslug = str(titleslug)
        monitored = str(True)
        seasonFolder = str(True)
        var = len(season)
        var -= 1
        s = {}
        seasons = []
        
        '''very kludgey, if you return the seasons starting at 0 it fails. So we have to go backwards from the last season 
        You also can't have double quotes which is why we build another dict to remove them from the json
        and lastly, we have to roll it all into a list'''
        for increment in xrange (var, 0, -1):
            if __name__ == '__main__':
                try:
                    s = {'seasonNumber': var, 'monitored': True}
                    seasons.append(s)
                    var -= 1
                except:
                    break
    # the following 2 lines are added to compensate for Sonarr incorrectly looking for a images entry in the add show post
    # remove the 2 lines below when Sonarr is working correclty and replace with the following line
        #    payload = {"title": title, "seasons": seasons, "rootFolderPath": path, "seasonFolder": seasonFolder, "monitored": monitored, "tvdbId": tvdbId, "seriestype": seriestype, "titleSlug": titleslug, "qualityProfileId": qualityprofile}
        images = [];
        payload = {"title": title, "seasons": seasons, "rootFolderPath": path, "seasonFolder": seasonFolder, "monitored": monitored, "tvdbId": tvdbId, "seriestype": seriestype, "titleSlug": titleslug, "qualityProfileId": qualityprofile, "images": images}
    #--------------------------------------------------------------------
        params = '/api/Series/'
        titletemp = payload['titleSlug']
        sonarr = sonarr_api(params=params)
        title = []
        var = 0
        for increment in sonarr:
            title.append(sonarr[var]['titleSlug'])
            var += 1
        
        var = 0
        for increment in title:
            if str.find(str(title[var]), str(titletemp)) != -1:
                return jsonify({'duplicate': True})
            var += 1
            
        api = get_setting_value('sonarr_api')
        url = sonarr_url() + '/api/Series/'
        headers = {'X-Api-Key': api}
        payload = json.dumps(payload)
        result = urllib2.Request(url, headers=headers, data=payload)
        urllib2.urlopen(result).read()
        return jsonify({'success': True})
    except Exception as e:
        log_exception(e)
        
    
    return jsonify({'success': False})


#Gets the snatched and downloaded history    
@app.route('/xhr/sonarr/get_history/')
def get_history():
    params = '/api/history?pageSize=25&page=1&sortKey=date&sortDir=desc'
    history = sonarr_api(params=params)
    properties = []
    for overview in history['records']:
        try:
            temp = []
            eventtypes = False
            overviews = overview['series']['overview']
            titles = overview['series']['title']
            episodetitle = overview['episode']['title']
            episode = overview['episode']['episodeNumber']
            season = overview['episode']['seasonNumber']
            try:
                path = overview['data']['importedPath']
                eventtypes = True
            except:
                pass
            date = overview['date'][:10]
            seriesid = overview['seriesId']
            temp.append(overviews)
            temp.append(titles)
            temp.append(episodetitle)
            temp.append(episode)
            temp.append(season)
            temp.append(path)
            temp.append(date)
            temp.append(seriesid)
            temp.append(eventtypes)
            properties.append(temp)
        except Exception as e:
            log_exception(e)

    return render_template('sonarr/history.html',
        webroot = str(sonarr_webroot_status()),
        lan = get_setting_value('sonarr_lan'),
        http = sonarr_http(),
        url = get_setting_value('sonarr_ip'),
        port = sonarr_port(),
        properties = properties,
        external_server = get_setting_value('sonarr_external_server')
    )

'''gets upcoming and missed shows for the past 14 days. everything listed "today" is 24 hours out, everything listed "tomorrow" is between 24-48 hours, everything listed "later" is past that,
and everything listed "missing" is stuff that hasn't been downloaded but has aired.    '''
@app.route('/xhr/sonarr/calendar')
def calendar():
    current_date = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.strptime(current_date, '%Y-%m-%d') - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    end_date = (datetime.datetime.strptime(current_date, '%Y-%m-%d') + datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    params = '/api/calendar?start=' + start_date + '&end=' + end_date
    calendar = sonarr_api(params=params)
    missed = {}
    today = {}
    tomorrow = {}
    later = {}
    for increment in calendar:
        banner = increment['seriesId']
        episodetitle = increment['title']
        airdateutc = increment['airDateUtc']
        airdate = datetime.datetime.strptime( airdateutc, "%Y-%m-%dT%H:%M:%SZ" )

        # convert UTC calendar time to local airdate
        localdelta = datetime.datetime.now() - datetime.datetime.utcnow()
        localairdate = datetime.datetime(year=airdate.year, month=airdate.month, day=airdate.day,
                       hour=airdate.hour, minute=airdate.minute, second=airdate.second) + localdelta

        airdatestr = airdate.strftime("%m/%d/%Y %H:%M:%S UTC")
        season = increment['seasonNumber']
        episode = increment['episodeNumber']
        episodeid = increment['id']
        episodetvdbid = increment['series']['tvdbId']
        try:
            episodeoverview = increment['overview']
        except KeyError:
            episodeoverview = ''
        if episodeoverview != '':
            overview = episodeoverview
        else:
            overview = increment['series']['overview']
    
        episodeid = increment['id']
        title = increment['series']['title']
        if localairdate < datetime.datetime.now():
            if str(increment['hasFile']) == 'False':
                missed.update({banner:[episodetitle, airdatestr, season, episode, overview, title, banner, episodeid, episodetvdbid]})
        elif  datetime.datetime.now().date() == localairdate.date():
            if datetime.datetime.now() < localairdate:
                today.update({banner:[episodetitle, airdatestr, season, episode, overview, title, banner, episodeid, episodetvdbid]})
        elif datetime.datetime.now() < localairdate:
            if localairdate.date() == (datetime.datetime.now().date() + datetime.timedelta(days=1)):
                tomorrow.update({banner:[episodetitle, airdatestr, season, episode, overview, title, banner, episodeid, episodetvdbid]})
            elif localairdate.date() > (datetime.datetime.now().date() + datetime.timedelta(days=1)):
                later.update({banner:[episodetitle, airdatestr, season, episode, overview, title, banner, episodeid, episodetvdbid]})

    tomorrowlist = sorted(tomorrow, key = lambda k: (datetime.datetime.strptime(tomorrow[k][1], "%m/%d/%Y %H:%M:%S UTC")) )
    todaylist = sorted(today, key = lambda k: (datetime.datetime.strptime(today[k][1], "%m/%d/%Y %H:%M:%S UTC")) )
    laterlist = sorted(later, key = lambda k: (datetime.datetime.strptime(later[k][1], "%m/%d/%Y %H:%M:%S UTC")) )
    missedlist = sorted(missed, key = lambda k: (datetime.datetime.strptime(missed[k][1], "%m/%d/%Y %H:%M:%S UTC")) )
    

    return render_template('sonarr/calendar.html',
        missedlist = missedlist,
        todaylist = todaylist,
        tomorrowlist = tomorrowlist,
        laterlist = laterlist,
        webroot = str(sonarr_webroot_status()),
        lan = get_setting_value('sonarr_lan'),
        url = get_setting_value('sonarr_ip'),
        http = sonarr_http(),
        external_server = get_setting_value('sonarr_external_server'),
        port = sonarr_port(),
        missed = missed,
        today = today,
        tomorrow = tomorrow,
        later = later
    )

#Search for entire series
@app.route('/xhr/sonarr/search_for_series/<seriesid>/')
def Series_search(seriesid):
    data=json.dumps({'name':'seriessearch', 'seriesId':seriesid})
    if run_command(data=data) == True:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False})