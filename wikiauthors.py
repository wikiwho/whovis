#!/bin/env python2

import WikiwhoRelationships
from copy import deepcopy
import operator
from sys import argv,exit
import getopt
from wmf import dump

#from django.utils import simplejson

def getStatsOfFile(revisions, order, relations, talk_pages):
     
    
    all_authors = set([])
    top_authors = {}
    k = 5
    
    data = {'absolute': {}, 'relative': {}, 'added': {}, 'totalActions': {}, 'negativeWordActions': {}, 'antagonizedEditors': {}, 'selfSupportActions': {}, 'talkPageEdits': {}} 

    prev_revision = None
    for (rev_id, vandalism) in order:
        
        #print "rev_id", rev_id, "vandalism", vandalism
        if (vandalism):
            data['relative'].update({rev_id : {'Length change (%)' : 0}})
            continue        
        
        # Compute authorship distribution information
        revision = revisions[rev_id]
        relation = relations[revision.wikipedia_id]
        authors = getAuthorshipDataFromRevision(revision)
        authDist, authDistAbsolut = sumAuthDist(authors, revision.total_tokens)
        all_authors.update(set(authors))
        
        #Compute top k contributors in this revision.
        top_k = sorted(authDist.iteritems(), key=operator.itemgetter(1), reverse=True)[:k]
        top_authors.update({rev_id : dict(top_k)})
        
        # Compute length change in percentage.
        if (prev_revision == None):
            lengthChange = 0
        else:
            lengthChange = ((revision.total_tokens - revisions[prev_revision].total_tokens) / float(revisions[prev_revision].total_tokens)) 
        
        # Compute number of total word actions.
        totalActions = {revision.contributor_name : (sum(relation.deleted.values()) + sum(relation.reintroduced.values()) + (sum(relation.redeleted.values()) + sum(relation.revert.values())))}
        
        # Compute number of negative word actions.
        negativeActions = {revision.contributor_name : ((sum(relation.deleted.values()) + sum(relation.revert.values())))}
        
        # Compute number of antagonized editors.
        antagonizedEditors = set([])
        for r in relation.deleted.keys():
            antagonizedEditors.add(revisions[r].contributor_name)
        for r in relation.revert.keys():
            antagonizedEditors.add(revisions[r].contributor_name)
        antagonizedEditors = {revision.contributor_name : len(antagonizedEditors)}
        
        # Compute number of negative word actions.
        selfSupportActions = {revision.contributor_name : ((sum(relation.self_redeleted.values()) + sum(relation.self_reintroduced.values())))}
        
        # Compute number of added new words.
        addedWords = {revision.contributor_name : relation.added}
        
        # Compute number of talk page edits since last (article) revision.
        talkPageEdits = 0
        #print "name", revision.contributor_name, "talkPages", talk_pages.keys()
        if (revision.contributor_name in talk_pages.keys()):
            while len(talk_pages[revision.contributor_name]) > 0:
                if (talk_pages[revision.contributor_name][0] <= revision.timestamp):
                    talkPageEdits = talkPageEdits + 1
                    talk_pages[revision.contributor_name].pop(0)
                else:
                    break
        talkPageEdits = {revision.contributor_name : talkPageEdits}
                
        
        # Update of stats.
        authDist.update({'Length change (%)' : lengthChange})
        data['relative'].update({rev_id : authDist})
        data['absolute'].update({rev_id : authDistAbsolut})
        data['negativeWordActions'].update({rev_id : negativeActions})
        data['antagonizedEditors'].update({rev_id : antagonizedEditors})
        data['added'].update({rev_id : addedWords})
        data['selfSupportActions'].update({rev_id : selfSupportActions})
        data['totalActions'].update({rev_id : totalActions})
        data['talkPageEdits'].update({rev_id : talkPageEdits})
        
        
        prev_revision = rev_id
        
        #print "data", data

    return data, all_authors, top_authors


def sumAuthDist(authors, length):
    wordCount = {}
    wordAbsolute = {}

    for author in authors:
        if(author in wordCount.keys()):
            wordCount[author] = wordCount[author]+1
            wordAbsolute[author] = wordAbsolute[author]+1
        else:
            wordCount[author] = 1
            wordAbsolute[author] = 1
            
    for author in wordCount.keys():
        wordCount[author] = wordCount[author]/float(length) 
        

    return wordCount, wordAbsolute


def topAuthors(top):
    
    authors = set([])
    
    for rev_id in top.keys():
        authors = authors.union(set(top[rev_id].keys()))
        
    return authors



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
                authors.append(word.author_name)
                #if (len(word.deleted)>1):
                #    print word.value, "deleted", len(word.deleted)

    
    return authors


def printStats(stats, all_authors, order):
    
    # Initialize stats to print.
    finalStats = {}
    total_words_author = {}
    #print "stats.keys()", stats.keys()
    for s in stats.keys():
        finalStats.update({s: {}})
                          
                
    count = 0
    #print "order", order
    for (rev_id, vandalism) in order:
        
        for author in all_authors:
            
            for stype in finalStats.keys():
            
                
                    
                # It was not vandalism.
                #print "stype", stype, "rev_id", rev_id, "stats[stype]", stats[stype]
                if not(vandalism) and author in stats[stype][rev_id].keys():
                    
                    if author in total_words_author.keys():
                        total_words_author[author] = total_words_author[author] + stats[stype][rev_id][author]
                    else:
                        total_words_author.update({author : stats[stype][rev_id][author]})
            
                    if author in finalStats[stype].keys():
                        finalStats[stype][author].append({"x": count, "y": stats[stype][rev_id][author], "z": rev_id})
                    else:
                        finalStats[stype].update({author: [{"x": count, "y": stats[stype][rev_id][author], "z": rev_id}]})
            
                # Vandalism.
                else:
                    if author in finalStats[stype].keys():
                        finalStats[stype][author].append({"x": count, "y": 0, "z": rev_id})
                    else:
                        finalStats[stype].update({author: [{"x": count, "y": 0, "z": rev_id}]})

        count = count + 1
    
    example = ""
    #example =  "\"relative\": "+ convert(finalStats['relative']) + ","
    example = example + "\"absolute\": " + convert(finalStats['absolute']) + ","
    example = example + "\"totalActions\": " + convert(finalStats['totalActions']) + ","
    example = example + "\"negativeActions\": " + convert(finalStats['negativeWordActions']) + ","
    example = example + "\"antagonizedEditors\": " + convert(finalStats['antagonizedEditors']) + ","
    example = example + "\"selfSupportActions\": " + convert(finalStats['selfSupportActions']) + ","
    #example = example + "\"talkPageEdits\": " + convert(finalStats['talkPageEdits']) + ","
    example = example + "\"added\": " + convert(finalStats['added']) 
    
    print "authorship = {" + example + "};"
    return total_words_author  

def printAuthors(authors, words_per_author): 
    
    var_author = "var author%i% = \"%author%\";"
    #var_mydata = "var mydata_rel%i% = authorship[\"talkPageEdits\"][author%i%];"
    var_mydata2 = "var mydata_abs%i% = authorship[\"absolute\"][author%i%];"
    all_data = []
    
    i = 1
    
    
    
    for author in sorted(words_per_author, key=words_per_author.get, reverse=True):
        
        if author in authors:
            #author = str(author)
            print var_author.replace("%i%", str(i)).replace("%author%", author)
            #print var_mydata.replace("%i%", str(i))
            print var_mydata2.replace("%i%", str(i))
            if (i > 1):
                #all_data.append({"\"key\"": "author%i%".replace("%i%", str(i)) + "+ \" (talkPageEdits)\"", "\"values\"": "mydata_rel%i%".replace("%i%", str(i)), "\"disabled\"": "\"true\""})
                all_data.append({"\"key\"": "author%i%".replace("%i%", str(i)) + "+ \" (Absolute)\"", "\"values\"": "mydata_abs%i%".replace("%i%", str(i)), "\"disabled\"": "\"true\""})
            else:
                #all_data.append({"\"key\"": "author%i%".replace("%i%", str(i)) + "+ \" (talkPageEdits)\"", "\"values\"": "mydata_rel%i%".replace("%i%", str(i))})
                all_data.append({"\"key\"": "author%i%".replace("%i%", str(i)) + "+ \" (Absolute)\"", "\"values\"": "mydata_abs%i%".replace("%i%", str(i))})
            
            i = i + 1
    
    #all_data.append({"\"key\"": "\"Length change (%)\"", "\"values\"": "example[\"relative\"][\"Length change (%)\"]"})   
    print "var alldata = " + str(all_data).replace('\'','') +";"
    #print "var alldata = " + convert(all_data) +";"
    
def processTalkPages(file_name):
    
    talk_pages = {}
    
    # Access the file.
    dumpIterator = dump.Iterator(file_name)
    
    # Iterate over pages of the dump.
    for page in dumpIterator.readPages():
        
        # Iterate over revisions of the article.
        for revision in page.readRevisions():
            
            contributor_name = revision.getContributor().getUsername().encode("utf-8")
            
            if (contributor_name in talk_pages.keys()):    
                talk_pages[contributor_name].append(revision.getTimestamp())
            else:
                talk_pages.update({contributor_name : [revision.getTimestamp()]})
            
    return talk_pages
    
def convert(data):
    
    mydata = []
    
    for author in data.keys():
        mydata.append('"' + str(author) + '"' + ":" + str(data[author]))

    return "{" + ",".join(mydata) + "}"
    
 
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
    pos = file_name.rfind("/")
    talk_file = file_name[0:pos+1] + "talk_" + file_name[pos+1:]
    (revisions, order, relations)  = WikiwhoRelationships.analyseArticle(file_name)
    #print "HERE ... order", order

    if (output == None or output == 'json'):
        # Compute statistics
        talk_pages = processTalkPages(talk_file)
        stats, all_authors, top_authors = getStatsOfFile(revisions, order, relations, talk_pages)
        words_per_author = printStats(stats, all_authors, order)
        final_top = topAuthors(top_authors)
        printAuthors(final_top, words_per_author)
        processTalkPages(talk_file)
        
        
    elif (output == 'table'):
        WikiwhoRelationships.printRelationships(relations, order) 
    else:
        print "Output format", output, "not supported"
        
