#!/bin/env python2

import os
import WikiwhoRelationships
from copy import deepcopy
import operator
from sys import argv,exit
import getopt
from wmf import dump
from structures.Revision import Revision
import re
import datetime
#from django.utils import simplejson

def getStatsOfFile(revisions, order, relations, tags):
     
    statData = []
    
    editDistSum = {}
    totalEditCount = 0
    all_authors = set([])
    all_editors = []
    prev_revision = None
    outgoing_negative_actions = {}
    incoming_negative_actions = {}
    self_reintroductions = []
    self_supports = []
    
    all_antagonized_editors = []
    all_supported_editors = []
    
    for (rev_id, vandalism) in order:
        
        
        
        if (vandalism):
            data = {'revision' : rev_id, 
                    'wikiGini V1':0, 
                    #'wikiGini V2':0, 
                    #'totalLength': 0, 
                    'lengthChange' : 0, 
                    'editRapidness': 0, 
                    'antagonizedEditors': 0, 
                    'antagonized_editors_avg_w1' : 0,
                    'antagonisticActions': 0, 
                    'supportedEditors': 0, 
                    'supported_editors_avg_w1' : 0,
                    'supportiveActions': 0,
                    #'tokenActions': 0, 
                    'giniEditorship': 0, 
                    'giniEditorship_w1': 0,
                    'giniOutgoingNegativeActions': 0,
                    'giniIncomingNegativeActions': 0, 
                    'selfReintroductionRatio': 0,
                    'selfReintroductionRatio_avg_w1':0, 
                    'selfSupportRatio': 0,
                    'selfSupportRatio_avg_w1': 0, 
                    'statEditors': 0, 
                    #'vandalism': 1,
                    'maintained': 0, 
                    'npov': 0, 
                    'goodArticle': 0, 
                    'featuredArticle': 0, 
                    'disputed': 0,
                    'protected': 0} 
            statData.append(data)
            #prev_revision = rev_id   
            continue        
        
        # Compute authorship distribution information
        revision = revisions[rev_id]
        relation = relations[revision.wikipedia_id]
        authors = getAuthorshipDataFromRevision(revision)
        all_authors.update(set(authors))
        authDistSum = sumAuthDist(authors)
        sortedAuthDistSum = sorted(authDistSum.iteritems(), key=operator.itemgetter(1))
        totalWordCount = len(authors)
        totalAuthorCountAS = len(sortedAuthDistSum)
        
        # Compute editorship distribution information
        all_editors.append(revision.contributor_name)
        editDistSum = sumAuthDist(all_editors)
        sortedEditDistSum = sorted(editDistSum.iteritems(), key=operator.itemgetter(1))
        
        
            
        
        # editorship with different windows
        window1 = 50
        #window2 = 20
        
        # editorship with window1
        editDistSum_w1 = None
        if (len(all_editors)>=window1):
            editDistSum_w1 = sumAuthDist(all_editors[len(all_editors)-window1:])
            sortedEditDistSum_w1 = sorted(editDistSum_w1.iteritems(), key=operator.itemgetter(1))
            
        # editorship with window2
        #editDistSum_w2 = None
        #if (len(all_editors)>=window2): 
        #    editDistSum_w2 = sumAuthDist(all_editors[len(all_editors)-window2:])
        #    sortedEditDistSum_w2 = sorted(editDistSum_w2.iteritems(), key=operator.itemgetter(1))

        # Compute wikigini: V1
        i = 1
        res = 0
        for tup in sortedAuthDistSum:
            res = res + (i * tup[1])
            i = i + 1        
        wikiGini = ((2.0 * res)/ (len(sortedAuthDistSum) * totalWordCount)) - ((len(sortedAuthDistSum) + 1.0   ) / len(sortedAuthDistSum))  
        
        # Compute wikigini: V2   
        i = len(all_authors) - len(sortedAuthDistSum) + 1
        res = 0
        for tup in sortedAuthDistSum:
            res = res + (i * tup[1])
            i = i + 1  
        wikiGini2 = ((2.0 * res)/ (len(all_authors) * totalWordCount)) - ((len(all_authors) + 1.0   ) / len(all_authors))  
        
        # Compute length change in percentage
        if (prev_revision == None):
            lengthChange = 0
        else:
            lengthChange = ((revision.length - revisions[prev_revision].length) / float(revisions[prev_revision].length)) 
            
        # Compute edit rapidness
        if (prev_revision == None):
            editRapidness = 0
        else:
            editRapidness = (revision.timestamp - revisions[prev_revision].timestamp) / 3600.0
        
        # antagonized_editors: Revert actions + delete actions in revision (distinct editors)
        antagonized_editors = set([])
        for elem in relation.revert.keys():
            antagonized_editors.add(revisions[elem].contributor_id)
        for elem in relation.deleted.keys():
            antagonized_editors.add(revisions[elem].contributor_id)   
            
        all_antagonized_editors.append(len(antagonized_editors))
        
        antagonized_editors_avg_w1 = 0
        if (len(all_antagonized_editors) >= window1):
            antagonized_editors_avg_w1 = sum(all_antagonized_editors[len(all_antagonized_editors)-window1:]) / float(window1)
        
        # antagonistic_actions: Revert actions + delete actions in revision (number of tokens)    
        antagonistic_actions = 0
        for elem in relation.revert.keys():
            antagonistic_actions = antagonistic_actions + relation.revert[elem]
        for elem in relation.deleted.keys():
            antagonistic_actions = antagonistic_actions + relation.deleted[elem]
            
        # supported_editors: reintroductions + redeletes (distinct editors)
        supported_editors = set([])
        for elem in relation.reintroduced.keys():
            supported_editors.add(revisions[elem].contributor_id)
        for elem in relation.redeleted.keys():
            supported_editors.add(revisions[elem].contributor_id)
         
        all_supported_editors.append(len(supported_editors))
        
        supported_editors_avg_w1 = 0
        if (len(all_supported_editors) >= window1):
            supported_editors_avg_w1 = sum(all_supported_editors[len(all_supported_editors)-window1:]) / float(window1)
        
           
        # supportive actions:  reintroductions + redeletes (number of tokens)
        supportive_actions = 0
        for elem in relation.reintroduced.keys():
            supportive_actions = supportive_actions + relation.reintroduced[elem]
        for elem in relation.redeleted.keys():
            supportive_actions = supportive_actions + relation.redeleted[elem]
            
        # total number of token actions
        tokenActions = 0
        for elem in relation.deleted.keys():
            tokenActions = tokenActions + relation.deleted[elem]
        for elem in relation.reintroduced.keys():
            tokenActions = tokenActions + relation.reintroduced[elem]
        for elem in relation.redeleted.keys():
            tokenActions = tokenActions + relation.redeleted[elem]
        for elem in relation.revert.keys():
            tokenActions = tokenActions + relation.revert[elem]
        tokenActions = tokenActions + relation.added
        
        # Compute gini editorship
        i = 1
        res = 0
        for tup in sortedEditDistSum:
            res = res + (i * tup[1])
            i = i + 1        
        giniEditorship = ((2.0 * res)/ (len(sortedEditDistSum) * len(all_editors))) - ((len(sortedEditDistSum) + 1.0   ) / len(sortedEditDistSum))  
        
        # Compute gini editorship with window 1
        giniEditorship_w1 = 0
        if (editDistSum_w1 != None):
            i = 1
            res = 0
            for tup in sortedEditDistSum_w1:
                res = res + (i * tup[1])
                i = i + 1        
            giniEditorship_w1 = ((2.0 * res)/ (len(sortedEditDistSum_w1) * window1)) - ((len(sortedEditDistSum_w1) + 1.0   ) / len(sortedEditDistSum_w1))  
        
        #giniEditorship_w2 = 0
        #if (editDistSum_w2 != None):
        #    i = 1
        #    res = 0
        #    for tup in sortedEditDistSum_w2:
        #        res = res + (i * tup[1])
        #        i = i + 1        
        #    giniEditorship_w2 = ((2.0 * res)/ (len(sortedEditDistSum_w2) * window2)) - ((len(sortedEditDistSum_w2) + 1.0   ) / len(sortedEditDistSum_w2))  
            
        # Computing gini of outgoing negative actions
        #if (revision.contributor_name in outgoing_negative_actions.keys()):
        if (revision.contributor_name in outgoing_negative_actions.keys()):
            outgoing_negative_actions.update({revision.contributor_name: outgoing_negative_actions[revision.contributor_name] + antagonistic_actions}) 
        else:
            outgoing_negative_actions.update({revision.contributor_name: antagonistic_actions}) 
        
             
        sortedNegDistSum = sorted(outgoing_negative_actions.iteritems(), key=operator.itemgetter(1))        
        i = 1
        res = 0
        for tup in sortedNegDistSum:
            res = res + (i * tup[1])
            i = i + 1    
        
        giniOutgoingNegativeActions = 0
        if (sum(outgoing_negative_actions.values()) > 0):
            # len(all_editors) represent the number of revisions
            giniOutgoingNegativeActions = ((2.0 * res)/ (len(sortedNegDistSum) * sum(outgoing_negative_actions.values()))) - ((len(sortedNegDistSum) + 1.0   ) / len(sortedNegDistSum))  
        #print rev_id , sortedNegDistSum, giniOutgoingNegativeActions 
        #print "giniOutgoingNegativeActions", giniOutgoingNegativeActions, "outgoing_negative_actions", outgoing_negative_actions
                
        # Computing gini of incoming negative actions
        for elem in relation.revert.keys():
            if elem in incoming_negative_actions.keys():
                incoming_negative_actions.update({elem : incoming_negative_actions[elem] + relation.revert[elem]}) 
            else:
                incoming_negative_actions.update({elem : relation.revert[elem]})
        for elem in relation.deleted.keys():
            if elem in incoming_negative_actions.keys():
                incoming_negative_actions.update({elem : incoming_negative_actions[elem] + relation.deleted[elem]}) 
            else:
                incoming_negative_actions.update({elem : relation.deleted[elem]})
        
        sortedNegDistSum = sorted(incoming_negative_actions.iteritems(), key=operator.itemgetter(1))        
        i = 1
        res = 0
        for tup in sortedNegDistSum:
            res = res + (i * tup[1])
            i = i + 1    
        
        giniIncomingNegativeActions = 0
        if (sum(incoming_negative_actions.values()) > 0):
            # len(all_editors) represent the number of revisions
            giniIncomingNegativeActions = ((2.0 * res)/ (len(sortedNegDistSum) * sum(incoming_negative_actions.values()))) - ((len(sortedNegDistSum) + 1.0   ) / len(sortedNegDistSum))  
        
        
        # self-reintroduction ratio
        all_actions = float(relation.added + sum(relation.deleted.values()) + sum(relation.redeleted.values()) + sum(relation.reintroduced.values()) + sum(relation.revert.values()) + sum(relation.self_reintroduced.values()) + sum(relation.self_redeleted.values()) + sum(relation.self_deleted.values()) + sum(relation.self_revert.values()))
        selfReintroductionRatio = 0
        if (all_actions != 0):
            selfReintroductionRatio = sum(relation.self_reintroduced.values()) / all_actions
        self_reintroductions.append(selfReintroductionRatio)
        
        selfReintroductionRatio_avg_w1 = 0
        if (len(self_reintroductions) >= window1):
            selfReintroductionRatio_avg_w1 = sum(self_reintroductions[len(self_reintroductions)-window1:]) / float(window1)
        
        # self-supported actions ration
        selfSupportRatio = 0
        if (all_actions != 0):
            selfSupportRatio = (sum(relation.self_reintroduced.values()) + sum(relation.self_redeleted.values())) / all_actions
        
        self_supports.append(selfSupportRatio)
        
        selfSupportRatio_avg_w1 = 0
        if (len(self_reintroductions) >= window1):
            selfSupportRatio_avg_w1 = (sum(self_reintroductions[len(self_reintroductions)-window1:]) + sum(self_supports[len(self_reintroductions)-window1:])) / float(window1)
        
        # Update editor stats
        statEditors = {}
        for a in authors:
            statEditors.update({a : {'wordOwnership' : authDistSum[a]/float(totalWordCount)}})
            
        #print rev_id, statEditors, statEditors[(rev_id, revision.contributor_name) ]
        positiveActions = 0
        negativeActions = 0
        if (all_actions != 0):
            positiveActions = ((sum(relation.redeleted.values()) + sum(relation.reintroduced.values()))) / all_actions
            negativeActions = ((sum(relation.deleted.values()) + sum(relation.revert.values()))) / all_actions
        
        if ((rev_id, revision.contributor_name) in statEditors.keys()):
            statEditors[revision.contributor_name].update({'positiveActions' : positiveActions})
            statEditors[revision.contributor_name].update({'negativeActions' : negativeActions})
        else:
            statEditors.update({revision.contributor_name : {'wordOwnership' : 0}})
            statEditors[revision.contributor_name ].update({'add' : relation.added})
            statEditors[revision.contributor_name ].update({'positiveActions' : positiveActions})
            statEditors[revision.contributor_name ].update({'negativeActions' : negativeActions})
        
        
        # Compute maintained tag
        maintained = 0
        npov = 0
        good_article = 0
        featured_article = 0
        disputed = 0 
        timestamps = tags.keys()
        timestamps.sort()
        for talk_ts in timestamps:
            if talk_ts <= revision.timestamp:
                for t in tags[talk_ts]:
                    
                    # Handling "maintained" tag
                    if (t["tagname"] == "maintained") and (t["type"] == "addition"):
                        maintained = 1
                    elif (t["tagname"] == "maintained") and (t["type"] == "removal"):
                        maintained = 0
                    
                    # Handling "npov" tag    
                    elif (t["tagname"] == "npov") and (t["type"] == "addition"):
                        npov = 1
                    elif (t["tagname"] == "npov") and (t["type"] == "removal"):
                        npov = 0
                        
                    # Handling "good article" tag
                    elif (t["tagname"] == "good article") and (t["type"] == "addition"):
                        good_article = 1
                    elif (t["tagname"] == "good article") and (t["type"] == "removal"):
                        good_article = 0
                        
                    # Handling "featured article" tag    
                    elif (t["tagname"] == "featured article") and (t["type"] == "addition"):
                        featured_article = 1    
                    elif (t["tagname"] == "featured article") and (t["type"] == "removal"):
                        featured_article = 0
                    
                    # Handling "disputed" tag
                    elif (t["tagname"] == "disputed") and (t["type"] == "addition"):
                        disputed = 1
                    elif (t["tagname"] == "disputed") and (t["type"] == "removal"):
                        disputed = 0
                        
        #################################################################################
    
        #print "revision.content", revision.content                
        if "featured article" in revision.content:
            #print "revision.content", revision.content
            featured_article = 1
        
        protected = 0 
        reglist = list()
        reglist.append({"tagname": "good article", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)good article((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
        #reglist.append({"tagname": "featured article", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)featured article((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
        #reglist.append({"tagname": "featured article", "regexp": re.compile('\|currentstatus=FA', re.IGNORECASE)})
        reglist.append({"tagname": "npov", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)(pov|npov)((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
        reglist.append({"tagname": "disputed", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)disputed((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
        #re_user = re.compile('({{|\[\[)user.*?[:|](.*?)[}/\]|]', re.IGNORECASE)
        reglist.append({"tagname": "protected", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)(pp-pc.?)((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
        
        for regexp in reglist:
            m = regexp["regexp"].search(revision.content)
            if m:
                if regexp["tagname"] == "disputed":
                    disputed = 1
                elif (regexp["tagname"] == "good article"):
                    good_article = 1
                elif (regexp["tagname"] == "npov"):
                    npov = 1
                elif (regexp["tagname"] == "protected"):
                    protected = 1
    
        data = {'revision' : revision.wikipedia_id, 
                'wikiGini V1':wikiGini, 
                #'wikiGini V2':wikiGini2, 
                #'totalLength': (revision.length)/(1024.0*1024.0), 
                'lengthChange' : lengthChange, 
                'editRapidness': editRapidness, 
                'antagonizedEditors': len(antagonized_editors), 
                'antagonized_editors_avg_w1' : antagonized_editors_avg_w1,
                'antagonisticActions': antagonistic_actions, 
                'supportedEditors': len(supported_editors), 
                'supported_editors_avg_w1' : supported_editors_avg_w1,
                'supportiveActions': supportive_actions,
                #'tokenActions': tokenActions, 
                'giniEditorship': giniEditorship, 
                'giniEditorship_w1': giniEditorship_w1,
                'giniOutgoingNegativeActions': giniOutgoingNegativeActions,
                'giniIncomingNegativeActions': giniIncomingNegativeActions, 
                'selfReintroductionRatio': selfReintroductionRatio,
                'selfReintroductionRatio_avg_w1':selfReintroductionRatio_avg_w1, 
                'selfSupportRatio': selfSupportRatio,
                'selfSupportRatio_avg_w1': selfSupportRatio_avg_w1, 
                'statEditors': statEditors, 
                #'vandalism': 0,
                'maintained': maintained, 
                'npov': npov, 
                'goodArticle': good_article, 
                'featuredArticle': featured_article,
                'disputed': disputed,
                'protected': protected}
        statData.append(data)
        
        #editorData = {'revision:', revision.wikipedia_id}
        #if (prev_revision != None):
        #    print "timestamp", revision.timestamp, revisions[prev_revision].timestamp, revision.timestamp - revisions[prev_revision].timestamp
        prev_revision = rev_id
        

    return statData

def saveStatsToFile(filename, stats):
    text_file = open(filename, "w")
    text_file.write(stats)
    text_file.close()

def sumAuthDist(authors):
    wordCount = {}

    for author in authors:
        if(author in wordCount.keys()):
            wordCount[author] = wordCount[author]+1
        else:
            wordCount[author] = 1

    return wordCount


def getTagDatesFromPage(file_name):
    # Compile regexp
    reglist = list()
    reglist.append({"tagname": "maintained", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)maintained((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
    reglist.append({"tagname": "good article", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)good article((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
    #reglist.append({"tagname": "featured article", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)featured article((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
    #reglist.append({"tagname": "featured article", "regexp": re.compile('\|currentstatus=FA', re.IGNORECASE)})
    reglist.append({"tagname": "npov", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)(pov|npov)((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
    reglist.append({"tagname": "disputed", "regexp": re.compile('\{\{(articleissues\|((?:(?!\}\}).)*\||)|multiple issues\|((?:(?!\}\}).)*\||)|)disputed((\||=)(?:(?!\}\}).)*|)\}\}', re.IGNORECASE)})
    re_user = re.compile('({{|\[\[)user.*?[:|](.*?)[}/\]|]', re.IGNORECASE)
    #"({{|\[\[)user[\s\S]*?[:|]([\s\S]*?)[}/\]|]"
    
    # Access the file.
    dumpIterator = dump.Iterator(file_name)
    
    # Revisions to compare.
    revision_curr = Revision()
    revision_prev = Revision()
    text_curr = None

    listOfTagChanges = {}
    all_contributors = {"maintained": {}, "good article": {}, "featured article": {}, "npov": {}, "disputed": {}}

    # Iterate over the pages.
    for page in dumpIterator.readPages():
        # Iterate over revisions of the article.
        i = 0
        prev_matched = list()
        for revision in page.readRevisions():
            revision.wikipedia_id = int(revision.getId())
            revision.timestamp = revision.getTimestamp()
            # Some revisions don't have contributor.
            if (revision.getContributor() != None):
                revision.contributor_id = revision.getContributor().getId()
                revision.contributor_name = revision.getContributor().getUsername()
            else:
                revision.contributor_id = 'Not Available'
                revision.contribur_name = 'Not Available'

            text_curr = revision.getText()
            if(text_curr):
                text_curr = text_curr.encode('utf-8')
                text_curr = text_curr.lower()
            else:
                continue
            matched = list()
            aux = list()

            for regexp in reglist:
                m = regexp["regexp"].search(text_curr)
                if m:
                    mc = re_user.split(m.group(0))
                    
                    i = 2
                    users = []
                    users.append(mc[2])
                    while (i+3 < len(mc)):
                        #print m[i+3]
                        users.append(mc[i+3])
                        i = i +3
                    
                    #print regexp["tagname"], contributor
                    #print regexp["tagname"], users
                    matched.append(regexp["tagname"])
                    aux.append((regexp["tagname"], users))
                    
                    ##
                    #m_user = re_user.search(m.group(0))
                    #contributor = m_user.group(2)
            if "|currentstatus=FA" in text_curr:
                matched.append("featured article")
                aux.append((revision.contributor_name,"featured article"))
                    

            # Calculate additions
            for (match, contributor) in aux:
                if not (match in prev_matched):
                    if not (revision.timestamp in listOfTagChanges.keys()):
                        listOfTagChanges[revision.timestamp] = list()
                    listOfTagChanges[revision.timestamp].append({"rev": revision.wikipedia_id, "type": "addition", "tagname": match, "wikiname": revision.contributor_name, "timestamp": revision.timestamp, "date": datetime.datetime.fromtimestamp(int(revision.timestamp)).strftime('%Y-%m-%d %H:%M:%S')})
                all_contributors[match].update({revision.timestamp : {"rev": revision.wikipedia_id, "user":contributor, "date":datetime.datetime.fromtimestamp(int(revision.timestamp)).strftime('%Y-%m-%d %H:%M:%S')}})
           
            # Calculate removals
            for match in prev_matched:
                if not (match in matched):
                    if not (revision.timestamp in listOfTagChanges.keys()):
                        listOfTagChanges[revision.timestamp] = list()
                    listOfTagChanges[revision.timestamp].append({"rev": revision.wikipedia_id, "type": "removal", "tagname": match, "wikiname": revision.contributor_name, "timestamp": revision.timestamp, "date": datetime.datetime.fromtimestamp(int(revision.timestamp)).strftime('%Y-%m-%d %H:%M:%S')})

            prev_matched = matched

    return listOfTagChanges, all_contributors



def getAuthorshipDataFromRevision(revision):
    #print "Printing authorship for revision: ", revision.wikipedia_id
    #text = []
    authors = []
    for hash_paragraph in revision.ordered_paragraphs:
        
        p_copy = deepcopy(revision.paragraphs[hash_paragraph])
        paragraph = p_copy.pop(0)
        
        for hash_sentence in paragraph.ordered_sentences:
            sentence = paragraph.sentences[hash_sentence].pop(0)
            
            for word in sentence.words:
                #text.append(word.value)
                authors.append(word.author_id)
    
    return authors


def printStats(stats):
    
    # Stats to print
    finalStats = {}
    
    # Mappings of revisions and fake ids
    revs = {}
    
    # Stats per revisions
    #wikiGini1 = []
    #wikiGini2 = []
    #totalLength = []
    lengthChange = []
    editRapidness = []
    #antagonizedEditors = []
    #antagonisticActions = []
    #supportedEditors = []
    #supportiveActions = []
    #tokenActions = []
    giniEditorship = []
    giniEditorship_w1 = []

    giniOutgoingNegativeActions = []
    giniIncomingNegativeActions = []
    #selfReintroductionRatio = []
    #selfSupportRatio = []
    #selfReintroductionRatio_avg_w1 = []
    #selfSupportRatio_avg_w1 = []
    #vandalism = []
    maintained = []
    npov = []
    goodArticle = []
    featuredArticle = []
    disputed = []
    protected = []
    antagonized_editors_avg_w1 = []
    #supported_editors_avg_w1 = []
    
    # Stats per editors
    editorStats = {}
    
    
    count = 0
    for elem in stats:
        #wikiGini1.append({"x": count, "y":  elem['wikiGini V1'], "z": elem["revision"]})
        #wikiGini2.append({"x": count, "y":  elem['wikiGini V2'], "z": elem["revision"]})
        #totalLength.append({"x": count, "y":  elem['totalLength'], "z": elem["revision"]})
        lengthChange.append({"x": count, "y":  elem['lengthChange'], "z": elem["revision"]})
        editRapidness.append({"x": count, "y":  elem['editRapidness'], "z": elem["revision"]})
        #antagonizedEditors.append({"x": count, "y":  elem['antagonizedEditors'], "z": elem["revision"]})
        antagonized_editors_avg_w1.append({"x": count, "y":  elem['antagonized_editors_avg_w1'], "z": elem["revision"]})
        
        #antagonisticActions.append({"x": count, "y":  elem['antagonisticActions'], "z": elem["revision"]})
        #supportedEditors.append({"x": count, "y":  elem['supportedEditors'], "z": elem["revision"]})
        #supported_editors_avg_w1.append({"x": count, "y":  elem['supported_editors_avg_w1'], "z": elem["revision"]})
        
        #supportiveActions.append({"x": count, "y":  elem['supportiveActions'], "z": elem["revision"]})
        #tokenActions.append({"x": count, "y":  elem['tokenActions'], "z": elem["revision"]})
        giniEditorship.append({"x": count, "y":  elem['giniEditorship'], "z": elem["revision"]})
        giniEditorship_w1.append({"x": count, "y":  elem['giniEditorship_w1'], "z": elem["revision"]})
        
        giniOutgoingNegativeActions.append({"x": count, "y":  elem['giniOutgoingNegativeActions'], "z": elem["revision"]})
        giniIncomingNegativeActions.append({"x": count, "y":  elem['giniIncomingNegativeActions'], "z": elem["revision"]})
        #selfReintroductionRatio.append({"x": count, "y":  elem['selfReintroductionRatio'], "z": elem["revision"]})
        #selfReintroductionRatio_avg_w1.append({"x": count, "y":  elem['selfReintroductionRatio_avg_w1'], "z": elem["revision"]})
        #selfSupportRatio.append({"x": count, "y":  elem['selfSupportRatio'], "z": elem["revision"]})
        #selfSupportRatio_avg_w1.append({"x": count, "y":  elem['selfSupportRatio_avg_w1'], "z": elem["revision"]})
        #vandalism.append({"x": count, "y":  elem['vandalism'], "z": elem["revision"]})
        maintained.append({"x": count, "y":  elem['maintained'], "z": elem["revision"]})
        npov.append({"x": count, "y":  elem['npov'], "z": elem["revision"]})
        goodArticle.append({"x": count, "y":  elem['goodArticle'], "z": elem["revision"]})
        protected.append({"x": count, "y":  elem['protected'], "z": elem["revision"]})
        featuredArticle.append({"x": count, "y":  elem['featuredArticle'], "z": elem["revision"]})
        disputed.append({"x": count, "y":  elem['disputed'], "z": elem["revision"]})
        #for editor in elem['statEditors']:
        
        count = count + 1
        
    
        
    #serie1  = {"key" : "WikiGini V1", "values": wikiGini1}
    #serie2  = {"key" : "WikiGini V2", "values": wikiGini2, "disabled": "true"}
    #serie3  = {"key" : "Total Length (MB)", "values": totalLength, "disabled": "true"}
    serie4  = {"key" : "Length Change (%)", "values": lengthChange, "disabled": "true"}
    serie5  = {"key" : "Edit Rapidness (h.)", "values": editRapidness, "disabled": "true"}
    #serie6  = {"key" : "Antagonized editors", "values": antagonizedEditors, "disabled": "true"}
    serie26 = {"key" : "Avg. editors disagreed with (window=50)", "values": antagonized_editors_avg_w1}
    
    #serie7  = {"key" : "Antagonized actions", "values": antagonisticActions, "disabled": "true"}
    #serie8  = {"key" : "Supported editors", "values": supportedEditors, "disabled": "true"}
    #serie27 = {"key" : "Avg. Supported editors (window=50)", "values": supported_editors_avg_w1, "disabled": "true"}
    
    #serie9  = {"key" : "Supportive actions", "values": supportiveActions, "disabled": "true"}
    #serie10 = {"key" : "Total token actions", "values": tokenActions, "disabled": "true"}
    serie11 = {"key" : "Gini editorship", "values": giniEditorship, "disabled": "true"}
    serie12 = {"key" : "Gini editorship (window=50)", "values": giniEditorship_w1, "disabled": "true"}
    
    serie14 = {"key" : "Gini outgoing dis. actions", "values": giniOutgoingNegativeActions, "disabled": "true"}
    serie15 = {"key" : "Gini incoming dis. actions", "values": giniIncomingNegativeActions, "disabled": "true"}
    #serie16 = {"key" : "Self-reintroduction ratio", "values": selfReintroductionRatio, "disabled": "true"}
    #serie17 = {"key" : "Avg. Self-reintroduction ratio (window=50)", "values": selfReintroductionRatio_avg_w1, "disabled": "true"}
    #serie18 = {"key" : "Self-support ratio", "values": selfSupportRatio, "disabled": "true"}
    #serie19 = {"key" : "Avg. Self-support ratio (window=50)", "values": selfSupportRatio_avg_w1, "disabled": "true"}
    #serie20 = {"key" : "Vandalism", "values": vandalism, "disabled": "true"}
    serie21 = {"key" : "Template:Maintained", "values": maintained, "disabled": "true"}
    serie22 = {"key" : "Template:NPOV", "values": npov, "disabled": "true"}
    serie23 = {"key" : "Template:Good Article", "values": goodArticle, "disabled": "true"}
    serie24 = {"key" : "Template:Featured Article", "values": featuredArticle, "disabled": "true"}
    serie25 = {"key" : "Template:Disputed", "values": disputed, "disabled": "true"}
    serie27 = {"key" : "Template:Protected", "values": protected, "disabled": "true"}
    
    finalStats.update({'revisions' : [serie26, serie4, serie5, serie14, serie15, serie11, serie12, serie21, serie22, serie23, serie24, serie25, serie27]})
    return "example = " + str(finalStats) + ";"   



def printStatsCSV(stats):
    
    # Stats to print
    finalStats = {}
    
    # Mappings of revisions and fake ids
    revs = {}
    
    # Stats per revisions
    wikiGini1 = []
    #wikiGini2 = []
    #totalLength = []
    lengthChange = []
    editRapidness = []
    antagonizedEditors = []
    antagonisticActions = []
    supportedEditors = []
    supportiveActions = []
    #tokenActions = []
    giniEditorship = []
    giniEditorship_w1 = []

    giniOutgoingNegativeActions = []
    giniIncomingNegativeActions = []
    selfReintroductionRatio = []
    selfSupportRatio = []
    selfReintroductionRatio_avg_w1 = []
    selfSupportRatio_avg_w1 = []
    #vandalism = []
    maintained = []
    npov = []
    goodArticle = []
    featuredArticle = []
    disputed = []
    antagonized_editors_avg_w1 = []
    supported_editors_avg_w1 = []
    
    # Stats per editors
    editorStats = {}
    

    lines = []
    
    header = ["WikiGini V1", "Length Change (%)"] #...
    
    ",".join(header)
    
    lines.append(header)
    
    for elem in stats:
        row = []
        row.append(elem["revision"])
        row.append(elem['wikiGini V1'])
        row.append(elem['lengthChange']) 
        row.append(elem['editRapidness'])
        row.append(elem['antagonizedEditors'])
        row.append(elem['antagonized_editors_avg_w1'])
        row.append(elem['antagonisticActions'])
        row.append(elem['supportedEditors'])
        # ...
        
        ",".join(row)
        lines.append(row)
        
    "\n".join(lines)
    
    
        # ...
        
#        antagonisticActions.append({"x": count, "y":  elem['antagonisticActions'], "z": elem["revision"]})
#        supportedEditors.append({"x": count, "y":  elem['supportedEditors'], "z": elem["revision"]})
#        supported_editors_avg_w1.append({"x": count, "y":  elem['supported_editors_avg_w1'], "z": elem["revision"]})
#        
#        supportiveActions.append({"x": count, "y":  elem['supportiveActions'], "z": elem["revision"]})
#        #tokenActions.append({"x": count, "y":  elem['tokenActions'], "z": elem["revision"]})
#        giniEditorship.append({"x": count, "y":  elem['giniEditorship'], "z": elem["revision"]})
#        giniEditorship_w1.append({"x": count, "y":  elem['giniEditorship_w1'], "z": elem["revision"]})
#        
#        giniOutgoingNegativeActions.append({"x": count, "y":  elem['giniOutgoingNegativeActions'], "z": elem["revision"]})
#        giniIncomingNegativeActions.append({"x": count, "y":  elem['giniIncomingNegativeActions'], "z": elem["revision"]})
#        selfReintroductionRatio.append({"x": count, "y":  elem['selfReintroductionRatio'], "z": elem["revision"]})
#        selfReintroductionRatio_avg_w1.append({"x": count, "y":  elem['selfReintroductionRatio_avg_w1'], "z": elem["revision"]})
#        selfSupportRatio.append({"x": count, "y":  elem['selfSupportRatio'], "z": elem["revision"]})
#        selfSupportRatio_avg_w1.append({"x": count, "y":  elem['selfSupportRatio_avg_w1'], "z": elem["revision"]})
#        #vandalism.append({"x": count, "y":  elem['vandalism'], "z": elem["revision"]})
#        maintained.append({"x": count, "y":  elem['maintained'], "z": elem["revision"]})
#        npov.append({"x": count, "y":  elem['npov'], "z": elem["revision"]})
#        goodArticle.append({"x": count, "y":  elem['goodArticle'], "z": elem["revision"]})
#        featuredArticle.append({"x": count, "y":  elem['featuredArticle'], "z": elem["revision"]})
#        disputed.append({"x": count, "y":  elem['disputed'], "z": elem["revision"]})
        #for editor in elem['statEditors']:
        
        
#        
#    
#        
#    serie1  = {"key" : "WikiGini V1", "values": wikiGini1}
#    #serie2  = {"key" : "WikiGini V2", "values": wikiGini2, "disabled": "true"}
#    #serie3  = {"key" : "Total Length (MB)", "values": totalLength, "disabled": "true"}
#    serie4  = {"key" : "Length Change (%)", "values": lengthChange, "disabled": "true"}
#    serie5  = {"key" : "Edit Rapidness (h.)", "values": editRapidness, "disabled": "true"}
#    serie6  = {"key" : "Antagonized editors", "values": antagonizedEditors, "disabled": "true"}
#    serie26 = {"key" : "Avg. Antagonized editors (window=50)", "values": antagonized_editors_avg_w1, "disabled": "true"}
#    
#    serie7  = {"key" : "Antagonized actions", "values": antagonisticActions, "disabled": "true"}
#    serie8  = {"key" : "Supported editors", "values": supportedEditors, "disabled": "true"}
#    serie27 = {"key" : "Avg. Supported editors (window=50)", "values": supported_editors_avg_w1, "disabled": "true"}
#    
#    serie9  = {"key" : "Supportive actions", "values": supportiveActions, "disabled": "true"}
#    #serie10 = {"key" : "Total token actions", "values": tokenActions, "disabled": "true"}
#    serie11 = {"key" : "Gini editorship", "values": giniEditorship, "disabled": "true"}
#    serie12 = {"key" : "Gini editorship (window=50)", "values": giniEditorship_w1, "disabled": "true"}
#    
#    serie14 = {"key" : "Gini outgoing neg. actions", "values": giniOutgoingNegativeActions, "disabled": "true"}
#    serie15 = {"key" : "Gini incoming neg. actions", "values": giniIncomingNegativeActions, "disabled": "true"}
#    serie16 = {"key" : "Self-reintroduction ratio", "values": selfReintroductionRatio, "disabled": "true"}
#    serie17 = {"key" : "Avg. Self-reintroduction ratio (window=50)", "values": selfReintroductionRatio_avg_w1, "disabled": "true"}
#    serie18 = {"key" : "Self-support ratio", "values": selfSupportRatio, "disabled": "true"}
#    serie19 = {"key" : "Avg. Self-support ratio (window=50)", "values": selfSupportRatio_avg_w1, "disabled": "true"}
#    #serie20 = {"key" : "Vandalism", "values": vandalism, "disabled": "true"}
#    serie21 = {"key" : "Maintained", "values": maintained, "disabled": "true"}
#    serie22 = {"key" : "NPOV", "values": npov, "disabled": "true"}
#    serie23 = {"key" : "Good Article", "values": goodArticle, "disabled": "true"}
#    serie24 = {"key" : "Featured Article", "values": featuredArticle, "disabled": "true"}
#    serie25 = {"key" : "Disputed", "values": disputed, "disabled": "true"}
    
    #finalStats.update({'revisions' : [serie1, serie4, serie5, serie6, serie26, serie7, serie8, serie27, serie9, serie11, serie12, serie14, serie15, serie16, serie17, serie18, serie19,  serie21, serie22, serie23, serie24, serie25]})
    #return "example = " + str(finalStats) + ";"   
    return lines



def printTags(contributors, revisions, order, file_name):
    
    maintainers = contributors["maintained"] 
    timestamps = maintainers.keys()
    timestamps.sort()
    
    csv_file = open(file_name, "w")    
    for (rev_id, vandalism) in order:
        users = None
        for talk_ts in timestamps:
            if not(vandalism) and talk_ts <= revisions[rev_id].timestamp:
                users = maintainers[talk_ts]["user"]
        
        if (users != None):
            csv_file.write(str(rev_id) + "\t" + "maintained" + "\t " + "\t".join(users) + "\n")
            
    csv_file.close()

                
def main(my_argv):
    inputfile = ''
    output = None

    if (len(my_argv) <= 3):
        try:
            opts, _ = getopt.getopt(my_argv,"i:",["ifile="])
        except getopt.GetoptError:
            print 'Usage: wikistats.py -i <inputfile> [-o <output>]'
            exit(2)
    else:
        try:
            opts, _ = getopt.getopt(my_argv,"i:o:",["ifile=","output="])
        except getopt.GetoptError:
            print 'Usage: wikistats.py -i <inputfile> [-o <output>]'
            exit(2)
    
    for opt, arg in opts:
        if opt in ('-h', "--help"):
            print "wikistats"
            print
            print 'Usage: wikistats.py -i <inputfile> [-rev <revision_id>]'
            print "-i --ifile File to analyze"
            print "-o --output Type of output. Options: 'json', 'table'. If not specified, JSON is the default."
            print "-h --help This help."
            exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--output"):
            output = arg
         
    return (inputfile,output)

if __name__ == '__main__':

    (file_name, output) = main(argv[1:])
    
    # Compute distribution information
    (revisions, order, relations)  = WikiwhoRelationships.analyseArticle(file_name)
    
    # Compute file name of talk page data file
    talkPageFileName = os.path.join(os.path.dirname(file_name), "talk_" + os.path.basename(file_name))
    tags, contributors = getTagDatesFromPage(talkPageFileName)
    
    
    printTags(contributors, revisions, order, file_name.replace(".xml", "_maintainers.csv"))

    if (output == None or output == 'json'):
        # Compute statistics
        stats = getStatsOfFile(revisions, order, relations, tags)
        print printStats(stats)
    
    elif (output == 'table'):
        WikiwhoRelationships.printRelationships(relations, order) 
        
    elif (output== 'csv'):
        # Compute statistics
        stats = getStatsOfFile(revisions, order, relations, tags)
        print printStatsCSV(stats)
        
    else:
        print "Output format", output, "not supported"
        
    #print stats
    #time2 = time()
        
    #pos = file_name.rfind("/")
    #print file_name[pos+1: len(file_name)-len(".xml")], time2-time1
        
    #printRelationships(relations, order)
    
    #printRevision(revisions[11])
    
    #print "Execution time:", time2-time1 


#saveStatsToFile("/home/jurkan/Dokumente/Informatik/ciseminar/software/nethackstats.json", getStatsOfFile("/home/jurkan/Dokumente/Informatik/ciseminar/software/nethack.xml"))
