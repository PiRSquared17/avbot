# -*- coding: utf-8 -*-

#todo
#ircbot https://fisheye.toolserver.org/browse/~raw,r=720/Bryan/TsLogBot/TsLogBot.py
#capacidad para leer CR de irc o de api

import datetime
import os
import random
import re
import time
import thread
import threading
import urllib
import socket
import sys

#modules from pywikipediabot
import query
import wikipedia

class Diegus(threading.Thread):
    def __init__(self, edit_props, fun):
        threading.Thread.__init__(self)
        self.edit_props = edit_props
        self.fun = fun
        self.page = edit_props['page']
        self.oldid = edit_props['oldid']
        self.diff = edit_props['diff']
        self.revcount = 10
        self.oldText = ''
        self.newText = ''
        self.pageHistory = []
        self.HTMLdiff = ''
        
    def run(self):
        #print self.page.title(), self.fun
        if self.fun == 'getOldVersionOldid':
            self.oldText = self.page.getOldVersion(self.oldid, get_redirect=True) #cogemos redirect si se tercia, y ya filtramos luego
            #print 'oldText', self.value, len(self.oldText)
        elif self.fun == 'getOldVersionDiff':
            self.newText = self.page.getOldVersion(self.diff, get_redirect=True) #cogemos redirect si se tercia, y ya filtramos luego
            #print 'newText', self.value, len(self.newText)
        elif self.fun == 'getVersionHistory':
            self.pageHistory = self.page.getVersionHistory(revCount=self.revcount)
        elif self.fun == 'getUrl':
            self.HTMLDiff = preferences['site'].getUrl('/w/index.php?diff=%s&oldid=%s&diffonly=1' % (self.diff, self.oldid))
    
    def getOldText(self):
        return self.oldText
    
    def getNewText(self):
        return self.newText
        
    def getPageHistory(self):
        return self.pageHistory
    
    def getHTMLDiff(self):
        return self.HTMLDiff

whitelistedgroups = ['checkuser', 'founder', 'researcher', 'bot', 'bureaucrat', 'abusefilter', 'oversight', 'steward', 'sysop', 'reviewer', 'import', 'rollbacker'] #list of trusted users
users = {} #dic with users sorted by group
groups = {}
colours = {
    'sysop': 'lightblue',
    'bot': 'lightpurple',
    'anon': 'lightyellow',
    '': 'lightgreen',
    }
"""
colourcodes = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 'a', 'b', 'c', 'd', 'e', 'f']
colournames = ['black', 'blue', 'green', 'aqua', 'red', 'purple', 'yellow', 'white', 'grey', 'light blue', 'light green', 'light aqua', 'light red', 'light purple', 'light yellow', 'bright white']
"""

preferences = {
    'language': 'en',
    'family': 'wikipedia',
    'botname': 'AVBOT',
    'newbie': 25,
    'rcAPI': False,
    'rcIRC': True,
    'server': 'irc.wikimedia.org',
    'channel': '#en.wikipedia',
    'ircname': 'AVBOT%d' % (random.randint(10000,99999)),
    'userinfofile': 'userinfo.txt',
    'test': True,
    'testwiki': False,
    'testfile': True,
    'testfilename': 'avbotreverts-testing.txt',
}

preferences['site'] = wikipedia.Site(preferences['language'], preferences['family'])
preferences['testwikipage'] = wikipedia.Page(preferences['site'], u'User:%s/Test' % (preferences['botname']))

regexps = [
    ur'(?i)\bf+u+c+k+\b',
    ur'(?i)\b(h+a+){2,}\b',
    ur'(?i)\bg+a+y+\b',
    ur'(?i)\bf+a+g+s*\b',
    ur'(?i)\ba+s+s+\b',
    ur'(?i)\bb+i+t+c+h+(e+s+)?\b',
    ]
cregexps = []

for regexp in regexps:
    cregexps.append(re.compile(regexp))

def loadUsersFromGroup(group):
    global users
    
    users[group] = []
    aufrom = '!'
    while aufrom:
        params = {
        'action': 'query',
        'list': 'allusers',
        'augroup': group,
        'aulimit': '500',
        'aufrom': aufrom,
        }
        data = query.GetData(params, site = preferences['site'])
        if not 'error' in data.keys():
            for item in data['query']['allusers']:
                users[group].append(item['name'])
        
        if 'query-continue' in data.keys():
            aufrom = data['query-continue']['allusers']['aufrom']
        else:
            aufrom = ''

def getUserInfo(user):
    editcount = 0
    if not isIP(user):
        if users.has_key(user):
            editcount = users[user]['editcount']
        
        if editcount > preferences['newbie']:
            if not random.randint(0, 20): #avoid update no newbies users too much
                return editcount
        
        params = {
        'action': 'query',
        'list': 'users',
        'ususers': user,
        'usprop': 'editcount|groups',
        }
        data = query.GetData(params, site=preferences['site'])
        if not 'error' in data.keys():
            editcount = 0
            if 'editcount' in query.GetData(params)['query']['users'][0].keys():
                editcount = int(query.GetData(params)['query']['users'][0]['editcount'])
            groups = []
            if 'groups' in query.GetData(params)['query']['users'][0].keys():
                groups = query.GetData(params)['query']['users'][0]['groups']
            users[user] = {'editcount': editcount, 'groups': groups, }
    
    #saving file
    if not random.randint(0, 100):
        saveUserInfo()

def getUserEditcount(user):
    if isIP(user):
        return 0
    
    if users.has_key(user):
        return users[user]['editcount']
    else:
        getUserInfo(user)
        return users[user]['editcount']

def getUserGroups(user):
    if isIP(user):
        return []
    
    if users.has_key(user):
        return users[user]['groups']
    else:
        getUserInfo(user)
        return users[user]['groups']

def saveUserInfo():
    f = open(preferences['userinfofile'], 'w')
    
    for user, props in users.items():
        print props
        line = u'%s\t%d\t%s\n' % (user, props['editcount'], ','.join(props['groups']))
        f.write(line.encode('utf-8'))
    
    f.close()

def loadUserInfo():
    global users
    
    if not os.path.exists(preferences['userinfofile']):
        #creating empty file
        saveUserInfo()
    
    f = open(preferences['userinfofile'], 'r')
    for line in f:
        line = unicode(line, 'utf-8')
        line = line[:-1]
        if line:
            user, editcount, groups = line.split('\t')
            users[user] = {'editcount': int(edits), 'groups': groups.split(',')}
    
    f.close()

def loadGroups():
    #Info about groups: http://www.mediawiki.org/wiki/Manual:User_rights
    global groups
    
    groups = []
    params = {
    'action': 'query',
    'meta': 'siteinfo',
    'siprop': 'usergroups',
    }
    data = query.GetData(params, site=preferences['site'])
    if not 'error' in data.keys():
        for item in query.GetData(params)['query']['usergroups']:
            groups.append(item['name'])

def loadUsers():
    if not groups:
        loadGroups()
    
    for group in whitelistedgroups:
        loadUsersFromGroup(group=group)
        print 'Loaded %d users in the group %s' % (len(users[group]), group)
    
    #previously blocked users and ips too?

def loadData():
    #users
    loadGroups()
    print 'Loaded %d groups: %s' % (len(groups), ', '.join(groups))
    print 'Loaded %d white groups: %s' % (len(whitelistedgroups), ', '.join(whitelistedgroups))
    
    loadUsers()
    loadUserInfo()
    print 'Loaded editcount for %d users' % (len(users.keys()))
    
    #other interesting data...

def editIsBlanking(edit_props):
    lenNew = len(edit_props['newText'])
    lenOld = len(edit_props['oldText'])
    
    if lenNew < lenOld and \
       not re.search(ur"(?i)# *REDIRECT", edit_props['newText']):
       #Avoid articles converted into #REDIRECT [[...]] and other legitimate blankings
        percent = (lenOld-lenNew)/(lenOld/100.0)
        if (lenOld>=500 and lenOld<1000 and percent>=90) or \
           (lenOld>=1000 and lenOld<2500 and percent>=85) or \
           (lenOld>=2500 and lenOld<5000 and percent>=75) or \
           (lenOld>=5000 and lenOld<10000 and percent>=72.5) or \
           (lenOld>=10000 and lenOld<20000 and percent>=70) or \
           (lenOld>=20000 and percent>=65):
            return True
    
    return False

def editIsTest(edit_props):
    
    
    return False

def editIsVandalism(edit_props):
    
    
    for regexp in cregexps:
        if re.search(regexp, edit_props['newText']) and \
           not re.search(regexp, edit_props['oldText']):
            return True
    
    return False

def editIsVanish(edit_props):
    return False

def userwarning():
    #enviar mensajes según el orden que ya tengan los de la discusión
    pass

def reverted():
    return False

def revert(edit_props, motive=""):
    #print "Detected edit to revert: %s" % motive
    
    #revertind code
    #revert all edits by this user
    stableoldid = ''
    stableuser = ''
    
    #print edit_props['history']
    for revision in edit_props['history']:
        if revision[2] != edit_props['user']:
            stableoldid = revision[0]
            stableuser = revision[2]
            break #nos quedamos con la más reciente que sea válida
    
    print '--->', edit_props['title'], stableoldid, edit_props['oldid'], '<----'
    if stableoldid and str(stableoldid) == str(edit_props['oldid']):
        if preferences['testwiki']:
            output = u'\n* %s [[%s]] [{{SERVER}}/w/index.php?diff=next&oldid=%s]' % (edit_props['timestamp'], edit_props['title'], edit_props['diff'])
            #preferences['testwikipage'].put(output, u'BOT - Adding one more: [[%s]]' % (edit_props['title']))
        elif preferences['testfile']:
            output = u'\n* %s [[%s]] [{{SERVER}}/w/index.php?diff=next&oldid=%s]' % (edit_props['timestamp'], edit_props['title'], edit_props['diff'])
            f=open(preferences['testfilename'], 'a')
            f.write(output.encode('utf-8'))
            f.close()
        else:
            pass
            #edit_props['page'].put(edit_props['oldText'], u'BOT - Reverting to %s version by [[User:%s|%s]]' % (stableoldid, stableuser, stableuser))
    
    #end code
    
    if reverted(): #a lo mejor lo ha revertido otro bot u otra persona
        pass
        #userwarning() 
    else:
        print "Somebody was faster than us reverting. Reverting not needed"

def editWar(edit_props):
    #comprueba si esa edición ya existe previamente en el historial, por lo que el usuario está insistiendo en que permanezca
    #primero con la longitud, y si hay semejanzas, entonces se compara con el texto completo
    return False

def analize(edit_props):
    if editWar(edit_props):
        #http://es.wikipedia.org/w/api.php?action=query&prop=revisions&titles=Francia&rvprop=size&rvend=2010-07-25T14:54:54Z
        print "Saltamos para evitar la guerra"
        return
    elif isDangerous(edit_props):
        #preparing data
        #get last edits in history
        t1=time.time()
        #simplificar las llamas a los hilos? pasar todos los parámetros o solo los necesarios?
        threadHistory = Diegus(edit_props, 'getVersionHistory')
        threadOldid = Diegus(edit_props, 'getOldVersionOldid')
        threadDiff = Diegus(edit_props, 'getOldVersionDiff')
        threadHTMLDiff = Diegus(edit_props, 'getUrl')
        threadHistory.start()
        threadOldid.start()
        threadDiff.start()
        threadHTMLDiff.start()
        threadHistory.join()
        edit_props['history'] = threadHistory.getPageHistory()
        #print edit_props['pageHistory']
        threadOldid.join()
        edit_props['oldText'] = threadOldid.getOldText()
        threadDiff.join()
        edit_props['newText'] = threadDiff.getNewText()
        #hacer mi propio differ, tengo el oldText y el newText, pedir esto retarda la reversión unos segundos #fix #costoso?
        threadHTMLDiff.join()
        edit_props['HTMLDiff'] = threadHTMLDiff.getHTMLDiff()
        edit_props['HTMLDiff'] = edit_props['HTMLDiff'].split('<!-- content -->')[1]
        edit_props['HTMLDiff'] = edit_props['HTMLDiff'].split('<!-- /content -->')[0] #No change
        #cleandata = cleandiff(editData['pageTitle'], editData['HTMLDiff']) #To clean diff text and to extract inserted lines and words
        line = u'%s %s %s %s %s %s' % (edit_props['title'], time.time()-t1, edit_props['history'][0][0], len(edit_props['oldText']), len(edit_props['newText']), len(edit_props['HTMLDiff']))
        #wikipedia.output(u'\03{lightred}%s\03{default}' % line)
        
        if editIsBlanking(edit_props):
            #revert(edit_props, motive="blanking")
            wikipedia.output(u'\03{lightred}-> *Blanking* detected in [[%s]] (%s)\03{default}' % (edit_props['title'], edit_props['change']))
        elif editIsTest(edit_props):
            wikipedia.output(u'\03{lightred}-> *Test* detected in [[%s]] (%s)\03{default}' % (edit_props['title'], edit_props['change']))
        elif editIsVandalism(edit_props):
            wikipedia.output(u'\03{lightred}-> *Vandalism* detected in [[%s]] (%s)\03{default}' % (edit_props['title'], edit_props['change']))
            revert(edit_props, motive="vandalism")
        elif editIsVanish(edit_props):
            wikipedia.output(u'\03{lightred}-> *Vanish* detected in [[%s]] (%s)\03{default}' % (edit_props['title'], edit_props['change']))
        else:
            pass

def isIP(user):
    t = user.split('.')
    if len(t) == 4 and \
       int(t[0])>=0 and int(t[0])<=255 and \
       int(t[1])>=0 and int(t[1])<=255 and \
       int(t[2])>=0 and int(t[2])<=255 and \
       int(t[3])>=0 and int(t[3])<=255:
        return True
    return False

def isDangerous(edit_props):
    useredits = getUserEditcount(edit_props['user'])
    
    #namespace filter
    if edit_props['page'].namespace() != 0:
        return False
    
    #anon filter
    if isIP(edit_props['user']):
        return True
    
    #group filter
    for whitelistedgroup in whitelistedgroups:
        if whitelistedgroup in users[edit_props['user']]['groups']:
            return False
        
    #edit number filter
    if useredits <= preferences['newbie']:
       return True
    
    return False

def fetchedEdit(edit_props):
    timestamp = edit_props['timestamp'].split('T')[1].split('Z')[0]
    change = edit_props['change']
    if change >= 0:
        change = '+%d' % (change)
    
    colour = 'lightyellow' #default
    if getUserEditcount(edit_props['user']) > preferences['newbie']:
        colour = 'lightgreen'
    for group in getUserGroups(edit_props['user']): #for users with importan flags (stewards, oversight) but probably low editcounts 
        if group in whitelistedgroups:
            colour = 'lightblue'
    if 'bot' in getUserGroups(edit_props['user']):
        colour = 'lightpurple'
    
    line = u'%s [[%s]] {\03{%s}%s\03{default}, %d ed.} (%s)' % (timestamp, edit_props['title'], colour, edit_props['user'], getUserEditcount(edit_props['user']), change)
    if not editWar(edit_props) and isDangerous(edit_props):
        wikipedia.output(u'== Analyzing ==> %s' % line)
        thread.start_new_thread(analize, (edit_props,))
    else:
        wikipedia.output(line)

def rcAPI():
    site = wikipedia.Site("en", "wikipedia")
    
    rctimestamp = ""
    rcs = site.recentchanges(number=1)
    for rc in rcs:
        rctimestamp = rc[1]
    
    rcdir = "newer"
    rchistory = []
    while True:
        rcs = site.recentchanges(number=100, rcstart=rctimestamp, rcdir=rcdir) #no devuelve los oldid, mejor hacerme mi propia wikipedia.query
        
        for rc in rcs:
            rcsimple = [rc[0].title(), rc[1], rc[2], rc[3]]
            if rcsimple not in rchistory:
                rchistory = rchistory[-1000:]
                rchistory.append(rcsimple)
                edit_props = {'page': rc[0], 'title': rc[0].title(), 'timestamp': rc[1], 'user': rc[2], 'comment': rc[3], }
                thread.start_new_thread(fetchedEdit, (edit_props,))
            rctimestamp = rc[1]
        time.sleep(3)

def rcIRC():
    #partially from Bryan ircbot published with MIT License http://toolserver.org/~bryan/TsLogBot/TsLogBot.py
    
    while True:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((preferences['server'], 6667))
            
            conn.sendall('USER %s * * %s\r\n' % (preferences['ircname'], preferences['ircname']))
            conn.sendall('NICK %s\r\n' % (preferences['ircname']))
            conn.sendall('JOIN %s\r\n' % (preferences['channel']))
    
            buffer = ''
            while True:
                if '\n' in buffer:
                    line = buffer[:buffer.index('\n')]
                    buffer = buffer[len(line) + 1:]
                    line = line.strip()
                    #print >>sys.stderr, line
                    
                    data = line.split(' ', 3)
                    if data[0] == 'PING':
                        conn.sendall('PONG %s\r\n' % data[1])
                    elif data[1] == 'PRIVMSG':
                        nick = data[0][1:data[0].index('!')]
                        target = data[2]
                        message = data[3][1:]
                        message = unicode(message, 'utf-8')
                        message = re.sub(ur'\x03\d{0,2}', ur'', message) #No colors
                        message = re.sub(ur'\x02\d{0,2}', ur'', message) #No bold
                        if target == preferences['channel']:
                            if message.startswith('\x01ACTION'):
                                pass #log('* %s %s' % (nick, message[8:]))
                            else:
                                #todo esta regexp solo vale para ediciones, las páginas nuevas tienen rcid= y no diff: http://en.wikipedia.org/w/index.php?oldid=385928375&rcid=397223378
                                m = re.compile(ur'(?im)^\[\[(?P<title>.+?)\]\]\s+(?P<flag>[NMB]*?)\s+(?P<url>http://.+?diff=(?P<diff>\d+?)\&oldid=(?P<oldid>\d+?))\s+\*\s+(?P<user>.+?)\s+\*\s+\((?P<change>[\-\+]\d+?)\)\s+(?P<comment>.*?)$').finditer(message)
                                for i in m:
                                    #flag, change, url
                                    edit_props = {'page': wikipedia.Page(preferences['site'], i.group('title')), 'title': i.group('title'), 'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'), 'user': i.group('user'), 'comment': i.group('comment'), 'diff': i.group('diff'), 'oldid': i.group('oldid'), 'change': int(i.group('change'))}
                                    thread.start_new_thread(fetchedEdit, (edit_props,))
                                pass #log('<%s>\t%s' % (nick, message))
                else:
                    data = conn.recv(1024)
                    if not data: raise socket.error
                    buffer += data
        except socket.error, e:
            print >>sys.stderr, 'Socket error!', e

def run():
    #irc or api
    #por cada usuairo que llegue nuevo list=users (us) para saber cuando se registró
    #evitar que coja ediciones repetidas
    
    if preferences["rcAPI"]:
        rcAPI()
    elif preferences["rcIRC"]:
        rcIRC()
    else:
        print 'You have to choice a feed mode: IRC or API'

def welcome():
    print "#"*80
    print "# Welcome to AVBOT 2.0 "
    print "#"*80
    
    #running message?
    #page = wikipedia.Page(preferences['site'], u'User:AVBOT/Sandbox')
    #page.put(u'%d' % (random.randint(1000, 9999)), u'BOT - Testing')

def bye():
    print "Bye, bye..."

def main():
    welcome()
    loadData()
    run()
    bye()

if __name__ == '__main__':
    main()
