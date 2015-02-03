#!/bin/env python2

import WikiwhoRelationships
from copy import deepcopy
from sys import argv,exit
import getopt
import numpy as np
import math
import random
import cgi
from structures.Word import Word
import operator


#from django.utils import simplejson

context = {}
context_obj = {}

random.seed(3)

def getGraph(filename):
    # Compute distribution information
    (revisions, order, relations)  = WikiwhoRelationships.analyseArticle(filename)
    
    # Graph structures.
    edges_rev = {}    
    nodes = {}
    
    # Metrics structures. 
    ordered_editors = []
    ordered_not_vandalism = []
    all_antagonized_editors = []
    all_supported_editors = []
    
    statsData = []
    contributors_rev = {}
    window = 50
    
    rev_counter = -1
    #C = {}
    
    for (revision, vandalism) in order:
        
        rev_counter = rev_counter + 1
        
        if (vandalism):
            #print "vandalism", revision
            statsData.append({'revision': revision, 
                          'distinct_editors': 0, 
                          'deletion_edges_contributors_w': 0,
                          'deletion_outgoing_ratio': 0,
                          'deletion_incoming_ratio': 0,
                          'deletion_reciprocity': 0,
                          'deletion_weight_avg': 0,
                          'bipolarity' : 0,
                          'deletion_weight' : 0,
                          'adjacency_matrix' : ([], [], {}, 0),
                          'reciprocity_matrix' : {},
                          'weight_matrix' : {},
                          'context' : {},
                          'antagonistic_focus_avg' : {},  
                          'negative_actions_weighted': 0, 
                          'wikigini': 0,
                          })
            continue

        relation = relations[revision]
        
        # Authorship distribution.
        authorship = getAuthorshipDataFromRevision(revisions[revision], order, rev_counter)
        totalWordCount = len(authorship)
        authDistSum = sumAuthDist(authorship)
        #print "authDistSum", authDistSum
        
        
        # List of editors in each order.
        ordered_editors.append(relation.author)
        ordered_not_vandalism.append(revision)
        
        if (relation.author in contributors_rev.keys()):
            contributors_rev[relation.author].append(revision)
        else:
            contributors_rev.update({relation.author : [revision]})
        
        # Update the nodes.
        if relation.author in nodes.keys():
            nodes[relation.author].append(revisions[revision].id)
        else:
            nodes.update({relation.author : [revisions[revision].id]})
 
        # Update the edges.
        # Edges: (edge_type, editor_source, rev_source, editor_target, rev_target, weight)
        edges_rev.update({revision : []})
        
        for elem in relation.deleted.keys():
            edges_rev[revision].append(("deletion", relation.author, revision, revisions[elem].contributor_name, elem, relation.deleted[elem]))
    
        for elem in relation.reintroduced.keys():
            edges_rev[revision].append(("reintroduction", relation.author, revision, revisions[elem].contributor_name, elem, relation.reintroduced[elem]))
                
        for elem in relation.redeleted.keys():
            edges_rev[revision].append(("redeletion", relation.author, revision, revisions[elem].contributor_name, elem, relation.redeleted[elem]))
        
        for elem in relation.revert.keys():
            edges_rev[revision].append(("revert", relation.author, revision,  revisions[elem].contributor_name, elem, relation.revert[elem]))
        
        
        
        # Calculate metrics.
        distinct_editors = 0
        deletion_edges_contributors_w = 0
        deletion_sender_ratio = 0
        deletion_receivers_ratio = 0
        deletion_reciprocal_edges = []
        deletion_reciprocity = 0
        deletion_edges_total = 0
        deletion_weight_avg = 0
        deletion_weight = 0
        bipolarity = 0
        #negative_actions_weighted = 0
        
        
        # Compute wikigini: V1
        i = 1
        res = 0
        sortedAuthDistSum = sorted(authDistSum.iteritems(), key=operator.itemgetter(1))
        for tup in sortedAuthDistSum:
            res = res + (i * tup[1])
            i = i + 1        
        wikiGini = ((2.0 * res)/ (len(sortedAuthDistSum) * totalWordCount)) - ((len(sortedAuthDistSum) + 1.0   ) / len(sortedAuthDistSum))  
        
        
        A = []
        editors_window = []
        R = {}
        C = {}
        C2 = {}
        C3 = {}
        W = {}
        X = {}
        antagonistic_focus_avg = {}
        #CC = {}

        
        window1 = len(ordered_editors)
        if (len(ordered_editors) >= window):
            window1 = window
            
        if True:
            deletion_sender_ratio = set([])
            deletion_receivers_ratio = set([])
            editors_window = list(set(ordered_editors[len(ordered_editors)-window1:]))
            A = np.zeros((len(editors_window), len(editors_window)))
            R = {}
            C = {}
            C2 = {}
            C3 = {}
            W = np.zeros((len(editors_window), len(editors_window)))
            X = {}
            target_revs = {}
            
                    

            for past_rev in ordered_not_vandalism[len(ordered_not_vandalism)-window1:]:
                
                #n =            
                for edge_pos in range(len(edges_rev[past_rev])-1, 0-1, -1):
                    
                    edge = edges_rev[past_rev][edge_pos]
                    
                    (edge_type, source, _, target, rev_target, weight) = edge
                    
                    
                            
                    if edge_type == "deletion" or edge_type == "revert":
                        
                        #print "edge", past_rev, rev_target, edge_type, source, target, weight
                        
                        # Checking if the target editor belongs to the window.
                        if (target in editors_window):
                            
                            # Counts the total number of edges in the window.
                            deletion_edges_total = deletion_edges_total + 1  
                        
                            # For metric 2: ratio of number of edges e only between editors in w.
                            deletion_edges_contributors_w = deletion_edges_contributors_w + 1 
                            
                            # For metric 3: ratio of n that sent nodes at least once in w.
                            deletion_sender_ratio.add(source) 
                        
                            # For metric 6: avg. weight of the edges e in w
                            deletion_weight_avg = deletion_weight_avg + weight
                            
                            # For metric: total negative actions (weight).
                            deletion_weight = deletion_weight + weight 
                            
                            # Update adjacency matrix
                            s = editors_window.index(source)
                            t = editors_window.index(target)
                            A[s][t] = A[s][t] + math.log10(1 + weight) + 1
                            A[t][s] = A[t][s] + math.log10(1 + weight) + 1
                            
                            W[s][t] = W[s][t] + weight
                            #W[t][s] = W[t][s] + weight
                            
                            
                            if (s,t) in R.keys():
                                R[(s,t)] = R[(s,t)] + weight # + 1
                            else:
                                R.update({(s,t) : weight})#1})
                                
                            if (past_rev in X.keys()):
                                if (target in X[past_rev].keys()):
                                    X[past_rev][target] = X[past_rev][target] + weight
                                else:
                                    X[past_rev].update({target : weight}) 
                            else:
                                X.update({past_rev : {target : weight}})
                                        
                            
                        # For metric 4: ratio of n that received edges at least once in w.
                        # Checking if the target revision belongs to the window.
                        if (rev_target in ordered_not_vandalism[len(ordered_not_vandalism)-window1:]):
                            deletion_receivers_ratio.add(target)
                        
                        # for metric 5: ratio of e that was reciprocal
                        # Don't discriminate edges that target revisions outside the window.    
                        if ((target, source) in deletion_reciprocal_edges):
                            deletion_reciprocal_edges.remove((target, source))
                            deletion_reciprocity = deletion_reciprocity + 1
                        else:
                            deletion_reciprocal_edges.append((source, target))
                
                
                        
            # Construction of context in window.
            # Iterate over each revision in the window.
            for past_rev in ordered_not_vandalism[len(ordered_not_vandalism)-window1:]:
                
                pos = ordered_not_vandalism.index(past_rev)
                prev_revision = ordered_not_vandalism[pos-1]
            
                # DETECT: UNDO of delete
                # Iterate over all the words of the current processed revision.
                for w in range(0, len(context[past_rev])):
                    
                    word = context[past_rev][w]
                    
                    for elem in word.deleted:
                        
                        # If it is not "self-action".
                        #and prev_revision not in word.used
                        
                        #if (past_rev == 15):
                        #    print word.value, revisions[past_rev].contributor_name, revisions[elem].contributor_name
                        #    print "elem < past_rev", elem < past_rev
                        #    print "revisions[past_rev].contributor_name != revisions[elem].contributor_name", revisions[past_rev].contributor_name != revisions[elem].contributor_name
                        #    print "revisions[elem].contributor_name in editors_window", revisions[elem].contributor_name in editors_window
                        #    print "....."
                        
                        if (elem < past_rev  and elem in revisions.keys() and revisions[past_rev].contributor_name != revisions[elem].contributor_name) and (revisions[elem].contributor_name in editors_window) and (prev_revision not in word.used):
                            
                            s = editors_window.index(revisions[past_rev].contributor_name)
                            t = editors_window.index(revisions[elem].contributor_name)
                        
                            # Add the context for the edge (s,t).
                            if (s,t) not in C2.keys():
                                C2.update({(s,t) : {'target': elem}})
                                target_revs.update({(s,t) : []})
                                
                            # Add the information about the context. 
                            if (past_rev,elem) not in C2[(s,t)]:
                                comment = "Comment: (Empty)"
                                if revisions[(past_rev)].comment != None:
                                    comment = "Comment: <i>" + revisions[past_rev].comment.encode("utf-8") + "</i>"
                                
                                #C2[(s,t)].update({(past_rev,elem) : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Undo of Deletion] " + revisions[past_rev].contributor_name + "->" + revisions[elem].contributor_name + ". Revision: " + str(past_rev) +". " +  comment + "</a>" ]})
                                C2[(s,t)].update({(past_rev,elem) : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Undo of Deletion] " + revisions[past_rev].contributor_name + "(" + str(past_rev) + ")->" + revisions[elem].contributor_name + "(" + str(elem) +"). " +  comment + "</a>" ]})
                                
                        
                            if (True):
                            
                                # If the word is not in the context: add it.
                                if  word not in C2[(s,t)][(past_rev,elem)]:
                                                                       
                                    #target_revs[(s,t)].append(word.revision)   
                                    
                                    # Add new line if this sentence is a new one in the context.                                 
                                    try: 
                                        if context[(past_rev)][w-1] not in C2[(s,t)][(past_rev,elem)]:
                                            C2[(s,t)][(past_rev,elem)].append("<br />")
                                    except:
                                        pass
                                    
                                    # Add 4 tokens of pre-context.
                                    for i in range(4,0,-1):
                                        try:
                                            if w-i >= 0 and context[(past_rev)][w-i] not in C2[(s,t)][(past_rev,elem)]:
                                                C2[(s,t)][(past_rev,elem)].append(context[(past_rev)][w-i])
                                                #C[(t,s)][past_rev].append(context[prev_revision][w-i])
                                                #if past_rev == 82285999:
                                                #    print "w-i", context[prev_revision][w-i], context[prev_revision][w-i].value
                                        except:
                                            pass
                                    
                                    # Append the word.
                                    C2[(s,t)][(past_rev,elem)].append(word)
                                    
                                    # Add 4 tokens of post-context.
                                    for i in range(1,5):
                                        try:
                                            if context[(past_rev)][w+i] not in C2[(s,t)][(past_rev,elem)]:
                                                C2[(s,t)][(past_rev,elem)].append(context[(past_rev)][w+i])
                                        except:
                                            pass
                                    
                                # If the word is already in context: add post-context.
                                else:
                                    
                                    # Add 4 tokens of post-context.    
                                    for i in range(1,5):
                                        try:
                                            if context[(past_rev)][w+i] not in C2[(s,t)][(past_rev)]:
                                                C2[(s,t)][(past_rev,elem)].append(context[(past_rev)][w+i])
                                        except:
                                            pass
                    
                        
                
                # DETECT: UNDO of re-introduction.
                # Iterate over all the words of the immediate previous revision. 
                for w in range(0, len(context[prev_revision])):
                    
                    word = context[prev_revision][w] 
                    
                    if past_rev not in word.deleted:
                        continue 
            
                    for elem in word.freq:
                             
                        # If it is not "self-delete".
                        if elem < past_rev and revisions[past_rev].contributor_name != revisions[elem].contributor_name and revisions[elem].contributor_name in editors_window:
                            s = editors_window.index(revisions[past_rev].contributor_name)
                            t = editors_window.index(revisions[elem].contributor_name)
                        
                            # Add the context for the edge (s,t).
                            if (s,t) not in C3.keys():
                                C3.update({(s,t) : {'target': elem}})
                                #target_revs.update({(s,t) : []})
                                
                            # Add the information about the context. 
                            if (past_rev,elem) not in C3[(s,t)]:
                                comment = "Comment: (Empty)"
                                if revisions[past_rev].comment != None:
                                    comment = "Comment: <i>" + revisions[past_rev].comment.encode("utf-8") + "</i>"
                                
                                #C3[(s,t)].update({(past_rev,elem) : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Undo of Re-introduction] " + revisions[past_rev].contributor_name + "->" + revisions[elem].contributor_name + ". Revision: " + str(past_rev) +". " +  comment + "</a>" ]})
                                C3[(s,t)].update({(past_rev,elem) : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Undo of Re-introduction] " + revisions[past_rev].contributor_name + "(" + str(past_rev) + ")"+ "->" + revisions[elem].contributor_name + "(" + str(elem) + ")" +". " +  comment + "</a>" ]})
                                
                        
                            if (True):
                            
                                # If the word is not in the context: add it.
                                if  word not in C3[(s,t)][(past_rev,elem)]:
                                                                       
                                    #target_revs[(s,t)].append(word.revision)   
                                    
                                    # Add new line if this sentence is a new one in the context.                                 
                                    try: 
                                        if context[(prev_revision)][w-1] not in C3[(s,t)][(past_rev,elem)]:
                                            C3[(s,t)][(past_rev,elem)].append("<br />")
                                    except:
                                        pass
                                    
                                    # Add 4 tokens of pre-context.
                                    for i in range(4,0,-1):
                                        try:
                                            if w-i >= 0 and context[(prev_revision)][w-i] not in C3[(s,t)][(past_rev,elem)]:
                                                C3[(s,t)][(past_rev,elem)].append(context[prev_revision][w-i])
                                                #C[(t,s)][past_rev].append(context[prev_revision][w-i])
                                                #if past_rev == 82285999:
                                                #    print "w-i", context[prev_revision][w-i], context[prev_revision][w-i].value
                                        except:
                                            pass
                                    
                                    # Append the word.
                                    C3[(s,t)][(past_rev,elem)].append(word)
                                    
                                    # Add 4 tokens of post-context.
                                    for i in range(1,5):
                                        try:
                                            if context[prev_revision][w+i] not in C3[(s,t)][(past_rev,elem)]:
                                                C3[(s,t)][(past_rev,elem)].append(context[prev_revision][w+i])
                                        except:
                                            pass
                                    
                                # If the word is already in context: add post-context.
                                else:
                                    
                                    # Add 4 tokens of post-context.    
                                    for i in range(1,5):
                                        try:
                                            if context[prev_revision][w+i] not in C3[(s,t)][(past_rev,elem)]:
                                                C3[(s,t)][(past_rev,elem)].append(context[prev_revision][w+i])
                                        except:
                                            pass

                
                    
                
                # DETECT: DELETION
                # Iterate over all the words of the immediate previous revision. 
                for w in range(0, len(context[prev_revision])):
                    
                    word = context[prev_revision][w] 
            
                    # If the word will be deleted in the window: detect deletion edge (s,t)  
                    if (past_rev in word.deleted and word.author_name in editors_window):
                        
                        s = editors_window.index(revisions[past_rev].contributor_name)
                        t = editors_window.index(word.author_name)
                        
                             
                        # If it is not "self-delete".
                        if revisions[past_rev].contributor_name != word.author_name:
                            
                            # Add the context for the edge (s,t).
                            if (s,t) not in C.keys():
                                C.update({(s,t) : {'target': word.author_name}})
                                #target_revs.update({(s,t) : []})
                                
                            # Add the information about the context. 
                            if past_rev not in C[(s,t)]:
                                comment = "Comment: (Empty)"
                                if revisions[past_rev].comment != None:
                                    comment = "Comment: <i>" + revisions[past_rev].comment.encode("utf-8") + "</i>"
                                
                                #C[(s,t)].update({past_rev : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Deletion] " + revisions[past_rev].contributor_name + "->" + word.author_name + ". Revision: " + str(past_rev) +". " +  comment + "</a>" ]})
                                C[(s,t)].update({past_rev : ["<a target=_blank href=http://en.wikipedia.org/w/index.php?&diff=" + str(past_rev) + "> [Deletion] " + revisions[past_rev].contributor_name + "(" + str(past_rev) + ")->" + word.author_name +"(" + str(prev_revision) +  "). " +  comment + "</a>" ]})
                                
                        
                            if (True):
                            
                                # If the word is not in the context: add it.
                                if  word not in C[(s,t)][past_rev]:
                                                                       
                                    #target_revs[(s,t)].append(word.revision)   
                                    
                                    # Add new line if this sentence is a new one in the context.                                 
                                    try: 
                                        if context[prev_revision][w-1] not in C[(s,t)][past_rev]:
                                            C[(s,t)][past_rev].append("<br />")
                                    except:
                                        pass
                                    
                                    # Add 4 tokens of pre-context.
                                    for i in range(4,0,-1):
                                        try:
                                            if w-i >= 0 and context[prev_revision][w-i] not in C[(s,t)][past_rev]:
                                                C[(s,t)][past_rev].append(context[prev_revision][w-i])
                                                #C[(t,s)][past_rev].append(context[prev_revision][w-i])
                                                #if past_rev == 82285999:
                                                #    print "w-i", context[prev_revision][w-i], context[prev_revision][w-i].value
                                        except:
                                            pass
                                    
                                    # Append the word.
                                    C[(s,t)][past_rev].append(word)
                                    
                                    # Add 4 tokens of post-context.
                                    for i in range(1,5):
                                        try:
                                            if context[prev_revision][w+i] not in C[(s,t)][past_rev]:
                                                C[(s,t)][past_rev].append(context[prev_revision][w+i])
                                        except:
                                            pass
                                    
                                # If the word is already in context: add post-context.
                                else:
                                    
                                    # Add 4 tokens of post-context.    
                                    for i in range(1,5):
                                        try:
                                            if context[prev_revision][w+i] not in C[(s,t)][past_rev]:
                                                C[(s,t)][past_rev].append(context[prev_revision][w+i])
                                        except:
                                            pass
                                   

            # Print the context for DELETE. 
            for (s,t) in C.keys():
                target = C[(s,t)]['target']
                del C[(s,t)]['target']
                for r in C[(s,t)].keys():
                    
                    info = ""
                    if (r in X.keys() and target in X[r].keys()):
                        info = "<b>Disagreement focus:</b> " + str(X[r][target] / float(sum(X[r].values()))) + "<br /><br />"
                        if ((s,t) in antagonistic_focus_avg.keys()):
                            antagonistic_focus_avg[(s,t)].append(X[r][target] / float(sum(X[r].values())))
                        else:
                            antagonistic_focus_avg.update({(s,t): [X[r][target] / float(sum(X[r].values()))]})
                    
                    
                    C[(s,t)].update({r : [info + printDeleteContext(C[(s,t)][r], r, target)]})  
                    
                    
            # Print the context for UNDO of delete. 
            for (s,t) in C2.keys():
                #target = C2[(s,t)]['target']
                del C2[(s,t)]['target']
                for (r,r2) in C2[(s,t)].keys():
                    target = r2
                    info = ""
                    if (r in X.keys() and revisions[target].contributor_name in X[r].keys()):
                    #    #print "X keys", X.keys(), "X[r] keys", r, target, X[r].keys(), X[r].values()
                        info = "<b>Disagreement focus:</b> " + str(X[r][revisions[target].contributor_name] / float(sum(X[r].values()))) + "<br /><br />"
                        
                        if ((s,t) in antagonistic_focus_avg.keys()):
                            antagonistic_focus_avg[(s,t)].append(X[r][revisions[target].contributor_name] / float(sum(X[r].values())))
                        else:
                            antagonistic_focus_avg.update({(s,t): [X[r][revisions[target].contributor_name] / float(sum(X[r].values()))]})
                        
                    #if past_rev == 9:
                    #    print "X", X, "info", info, "r", r, "target", target
                    if (s,t) in C.keys():
                        if (r in C[(s,t)].keys()):
                            C[(s,t)][r].append(printUndoOfDeletionContext(C2[(s,t)][(r,r2)], r, target))
                        else:
                            C[(s,t)].update({r : [info + printUndoOfDeletionContext(C2[(s,t)][(r,r2)], r, target)]})  
                    else:
                        C.update({(s,t) : {r : [info + printUndoOfDeletionContext(C2[(s,t)][(r,r2)], r, target)]}})
            
            
            # Print the context for UNDO of re-introduction. 
            for (s,t) in C3.keys():
                #target = C3[(s,t)]['target']
                del C3[(s,t)]['target']
                for (r,r2) in C3[(s,t)].keys():
                    target = r2
                    info = ""
                    if (r in X.keys() and revisions[target].contributor_name in X[r].keys()):
                    #    #print "X keys", X.keys(), "X[r] keys", r, target, X[r].keys(), X[r].values()
                        info = "<b>Disagreement focus:</b> " + str(X[r][revisions[target].contributor_name] / float(sum(X[r].values()))) + "<br /><br />"
                        
                        if ((s,t) in antagonistic_focus_avg.keys()):
                            antagonistic_focus_avg[(s,t)].append(X[r][revisions[target].contributor_name] / float(sum(X[r].values())))
                        else:
                            antagonistic_focus_avg.update({(s,t): [X[r][revisions[target].contributor_name] / float(sum(X[r].values()))]})    
                    #if past_rev == 9:
                    #    print "X", X, "info", info, "r", r, "target", target
                    if (s,t) in C.keys():
                        if (r in C[(s,t)].keys()):
                            C[(s,t)][r].append(printUndoOfReintroductionContext(C3[(s,t)][(r,r2)], r, target))
                        else:
                            C[(s,t)].update({r : [info + printUndoOfReintroductionContext(C3[(s,t)][(r,r2)], r, target)]})  
                    else:
                        C.update({(s,t) : {r : [info + printUndoOfReintroductionContext(C3[(s,t)][(r,r2)], r, target)]}})
                             
                        
            # 1: Number of distinct editors n that edited in window1.
            distinct_editors = len(set(ordered_editors[len(ordered_editors)-window1:]))                
            
            # 2: Ratio of # of edges e only between editors in w
            deletion_edges_contributors_w = deletion_edges_contributors_w / float(distinct_editors) 
                         
            # 3: Ratio of n that sent edges at least once in w 
            deletion_sender_ratio = len(deletion_sender_ratio) / float(distinct_editors)
            
            # 4: Ratio of n that received edges at least once in w 
            deletion_receivers_ratio = len(deletion_receivers_ratio) / float(distinct_editors)
            
            if (deletion_edges_total != 0):
                # 5: Ratio of e that was reciprocal
                deletion_reciprocity = deletion_reciprocity / float((deletion_edges_total / 2.0))
            
                # 6: Average weight of the edges e in w
                deletion_weight_avg = deletion_weight_avg / float(deletion_edges_total)
            else:
                deletion_reciprocity = 0
                
                deletion_weight_avg = 0
            
            
            #print "A before", A
            
            # Update the reciprocity on the weights of the adjacency matrix.
            for (s_index, t_index) in R.keys():
                #print "s_index", s_index, "t_index", t_index,  R
                #if ((t_index, s_index) in R.keys()):
                #    reciprocity = min(R[(s_index, t_index)], R[(t_index, s_index)])
                #else:
                #    reciprocity = 0
                A[s_index][t_index] = A[s_index][t_index] #+  (2*reciprocity)
                A[t_index][s_index] = A[t_index][s_index] #+  (2*reciprocity)
                
            
            eigenvalues, _ = np.linalg.eig(A)
            lambda_max = max(eigenvalues)
            lambda_min = min(eigenvalues)  
            
            bipolarity = 0
            if (lambda_max != 0):  
                bipolarity = -lambda_min / lambda_max 
                bipolarity = bipolarity.real
            #print "bipolarity", bipolarity, "lambda_min", lambda_min, "lambda_max", lambda_max
            #print "bipolarity", bipolarity
                
            #print "A after", A
                
            
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
        
            
        statsData.append({'revision': revision, 
                          'author': revisions[revision].contributor_name, 
                          'distinct_editors': distinct_editors, 
                          'deletion_edges_contributors_w': deletion_edges_contributors_w,
                          'deletion_sender_ratio': deletion_sender_ratio,
                          'deletion_receiver_ratio': deletion_receivers_ratio,
                          'deletion_reciprocity': deletion_reciprocity,
                          'deletion_weight_avg': deletion_weight_avg,
                          'deletion_weight': deletion_weight,
                          'antagonized_editors_avg_w1': antagonized_editors_avg_w1,
                          'supported_editors_avg_w1': supported_editors_avg_w1,
                          'bipolarity' : bipolarity, 
                          'adjacency_matrix' : (A, editors_window, authDistSum, totalWordCount),
                          'reciprocity_matrix' : R,
                          'weight_matrix' : W,
                          'context' : C,
                          'antagonistic_focus_avg' : antagonistic_focus_avg, 
                          'wikigini' : wikiGini})    
                                
    
    #for r in context.keys():
    #    print "-----"
    #    print r
    #    for w in context[r]:
    #        print w.value
    return statsData
    


def sumAuthDist(authors):
    wordCount = {}

    for author in authors:
        if(author in wordCount.keys()):
            wordCount[author] = wordCount[author]+1
        else:
            wordCount[author] = 1

    return wordCount

def getAuthorshipDataFromRevision(revision, order, rev):
    #print "Printing authorship for revision: ", revision.wikipedia_id, rev
    #text = []
    authors = []
    (rev_id, _) = order[rev]
    
    #global context_obj
    global context
    
    context.update({rev_id: []})
    
    for hash_paragraph in revision.ordered_paragraphs:
        
        p_copy = deepcopy(revision.paragraphs[hash_paragraph])
        paragraph = p_copy.pop(0)
        
        for hash_sentence in paragraph.ordered_sentences:
            sentence = paragraph.sentences[hash_sentence].pop(0)
            
            for i in range(0, len(sentence.words)):
                 
                word = sentence.words[i]
                #word in sentence.words:
                #text.append(word.value)
                authors.append(word.author_name)
                context[rev_id].append(word)
                
        #context[rev_id].append(word)
   
    return authors

def printDeleteContext(cc, rev, target_revs):#, source):
    
    mystr = ""
    for w in cc:
        if isinstance(w, Word):
            
            #if rev == 82784338:
            #    print w.value, "w.author_name", w.author_name, "target_revs", target_revs, "rev", rev, "w.deleted", w.deleted
            
            if (w.author_name == target_revs and rev in w.deleted):
                mystr = mystr + " <b><span class='text-danger'>" + cgi.escape(w.value)  + "</span></b> " # + "@"+ w.author_name + "</b> "
            else:
                mystr = mystr + " " + cgi.escape(w.value) # + "@"+ w.author_name
            #if ((w.revision in cc['revs']) and (source in w.deleted)):
            #    mystr = mystr + " <b>" + w.value + "</b> "# + "$"+ str(id(w)) + "</b> "
            #else:
            #    mystr = mystr + " " + w.value #+ "$"+ str(id(w))          
        else:
            mystr = mystr + " " + w
    
    mystr = mystr.replace('"', '&quot;')
    
    return mystr
    
    
def printUndoOfDeletionContext(cc, rev, target_revs):#, source):
    
    mystr = ""
    for w in cc:
        if isinstance(w, Word):
            
            #if (rev == 143602582):
            #    print "w.value", w.value, "target_revs", target_revs, "w.deleted", w.deleted
             
            if (target_revs in w.deleted):
                mystr = mystr + " <b><span class='text-success'>" + cgi.escape(w.value)  + "</span></b> " # + "@"+ w.author_name #+ "</b> "
            else:
                mystr = mystr + " " + cgi.escape(w.value) # + "@"+ w.author_name        
        else:
            mystr = mystr + " " + w
    
    mystr = mystr.replace('"', '&quot;')
    
    return mystr


def printUndoOfReintroductionContext(cc, rev, target_revs):#, source):
    
    mystr = ""
    for w in cc:
        if isinstance(w, Word):
            
            
            if (target_revs in w.freq  and rev in w.deleted):
                mystr = mystr + " <b><span class='text-danger'>" + cgi.escape(w.value)  + "</span></b> " # + "@"+ w.author_name + "</b> "
            else:
                mystr = mystr + " " + cgi.escape(w.value) # + "@"+ w.author_name
        
        else:
            mystr = mystr + " " + w
    
    mystr = mystr.replace('"', '&quot;')
    
    return mystr

def printContext(source, target):
    
    global context
    #print context
    full_str = ""
    #for (source, target) in context.keys():
    if True:
        #print
        sentences = context[(source, target)]
        mystr = "" 
        for s in sentences:
            for w in s:
                if (w.revision == target and source in w.deleted):
                    mystr = mystr + " <b>" + w.value + "$"+ str(id(w)) + "</b> "
                else:
                    mystr = mystr + " " + w.value + "$"+ str(id(w))
            
            #print mystr
            
            full_str = full_str + "<br />" + mystr
            mystr= "" 
    full_str = full_str.replace('"', '&quot;')
    
    return full_str

def printForD3(v, e, etype):
    
    v_dict = {}
    v_str = []
    e_str = []
    
    max_weight = 0
    for edge in e:
        ((source, target), edge_type, weight) = edge
        if (weight > max_weight):
            max_weight = weight
    
    for edge in e:
        ((source, target), edge_type, weight) = edge
        
        if (edge_type == etype):
            
            if (source not in v_dict.keys()):
                v_dict.update({source : len(v_str)})
                v_str.append("{\"name\": \"" + source + "\", \"group\":1}")
                
            if (target not in v_dict.keys()):
                v_dict.update({target : len(v_str)})
                v_str.append("{\"name\": \"" + target + "\", \"group\":1}")
        
            force = weight
            e_str.append("{\"source\":" + str(v_dict[source]) + ", \"target\":" + str(v_dict[target]) + ", \"value\":"+ str(force) + "}")
    
    print "graph={" + "\"nodes\": [" + ','.join(v_str) + "], \"links\": [" + ','.join(e_str)  + "]}"



def printTimeForD3(v, e, etype, graph):
    
    v_dict = {}


    print "graph={"
    
    count = 0
    for rev in graph.keys():
        
        v_str = []
        e_str = []
    
        for edge in graph[rev]['links']:
        
            (edge_type, source, target, weight) = edge
        
            if (edge_type == etype):
            
                if (source not in v_dict.keys()):
                    v_dict.update({source : len(v_str)})
                    v_str.append("{\"name\": \"" + source + "\", \"group\":1}")
                
                if (target not in v_dict.keys()):
                    v_dict.update({target : len(v_str)})
                    v_str.append("{\"name\": \"" + target + "\", \"group\":1}")
        
                    force = weight
                    e_str.append("{\"source\":" + str(v_dict[source]) + ", \"target\":" + str(v_dict[target]) + ", \"value\":"+ str(force) + "}")
    
        
        print str(count) + ": {" + "\"nodes\": [" + ','.join(v_str) + "], \"links\": [" + ','.join(e_str)  + "]},"
        count = count + 1
        
    print "}"


def printSnapshotsForD3(v, e, etype, graph):
    
    v_dict = {}
    v_str = []
    e_str = []

    print "graph={"
    
    count = 0
    for rev in graph.keys():
    
        for edge in graph[rev]['links']:
        
            (edge_type, source, target, weight) = edge
        
            if (edge_type == etype):
            
                if (source not in v_dict.keys()):
                    v_dict.update({source : len(v_str)})
                    v_str.append("{\"name\": \"" + source + "\", \"group\":1}")
                
                if (target not in v_dict.keys()):
                    v_dict.update({target : len(v_str)})
                    v_str.append("{\"name\": \"" + target + "\", \"group\":1}")
        
                    force = weight
                    e_str.append("{\"source\":" + str(v_dict[source]) + ", \"target\":" + str(v_dict[target]) + ", \"value\":"+ str(force) + "}")
    
        
        print str(count) + ": {" + "\"nodes\": [" + ','.join(v_str) + "], \"links\": [" + ','.join(e_str)  + "]},"
        count = count + 1
        
    print "}"

    
def printForNeo4J(g, v, e):
    
    code = []
    article_tpl = "(%article_id%:ARTICLE {title: '%article%'})"
    vertex_tpl = "(%editor%:EDITOR {name: '%editor%'})"
    edge_tpl = "(%source%)-[:%edge_type% {weight: %weight%}]->(%target%)"
    edge_article_tpl = "(%source%)-[:EDITED_BY {revisions:%revisions%}]->(%target%)"
    
    # Create edges to article.
    instance = article_tpl
    instance = instance.replace("%article%", g.encode("utf-8"))
    instance = instance.replace("%article_id%", g.encode("utf-8").replace(" ", "_"))
    code.append(instance)
    
    # Create nodes.
    for vertex in v.keys():
        instance = vertex_tpl
        instance = instance.replace("%editor%", vertex.encode("utf-8")) 
        code.append(instance)
        instance = edge_article_tpl
        instance = instance.replace("%source%", g.encode("utf-8").replace(" ", "_"))
        instance = instance.replace("%target%", vertex.encode("utf-8"))
        instance = instance.replace("%revisions%", str(v[vertex]))
        code.append(instance)
    
    # Create edges.
    for edge in e:
        ((source, target), edge_type, weight) = edge
        instance = edge_tpl
        instance = instance.replace("%source%", source.encode("utf-8"))
        instance = instance.replace("%edge_type%", edge_type.upper())
        instance = instance.replace("%weight%", str(weight))
        instance = instance.replace("%target%", target.encode("utf-8")) 
        code.append(instance)
        
    
        
    print "CREATE " + ",\n".join(code)

def printStats(stats, reciprocity):
    
    # Stats to print
    finalStats = []
    
    # Stats per revisions
    #distinct_editors = []
    #deletion_edges_contributors_w = []
    #deletion_outgoing_ratio = []
    #deletion_incoming_ratio = []
    deletion_reciprocity = []
    #deletion_weight_avg = []
    deletion_weight = []
    #antagonized_editors_avg_w1 = []
    #supported_editors_avg_w1 = []
    bipolarity = []
    weighted_reciprocity = []
    wikigini = []
    
    count = 0
    
    total_negative_actions = []
    
    #print "CHECK", len(stats), len(reciprocity)
    
    #for elem in reciprocity
    
    for elem in stats:
        total_negative_actions.append(elem['deletion_weight'])
    #print "total",  total_negative_actions
    
    max_total_negative_actions = max(total_negative_actions)
    max_reciprocity = max(reciprocity)
    #print "max",  max_total_negative_actions
    
    for i in range (0, len(stats)):
        elem = stats[i]
        elem2 = reciprocity[i]
        #distinct_editors.append({"x": count, "y":  elem['distinct_editors'], "z": elem["revision"]})
        #deletion_edges_contributors_w.append({"x": count, "y":  elem['deletion_edges_contributors_w'], "z": elem["revision"]})
        #deletion_outgoing_ratio.append({"x": count, "y":  elem['deletion_sender_ratio'], "z": elem["revision"]})
        #deletion_incoming_ratio.append({"x": count, "y":  elem['deletion_receiver_ratio'], "z": elem["revision"]})
        #deletion_reciprocity.append({"Revision": count, "Value":  elem['deletion_reciprocity'], "Wikipedia Revision": elem["revision"], "Metric": "Disagreement Reciprocity"})
        #deletion_weight_avg.append({"x": count, "y":  elem['deletion_weight_avg'], "z": elem["revision"]})
        #antagonized_editors_avg_w1.append({"x": count, "y":  elem['antagonized_editors_avg_w1'], "z": elem["revision"]})
        #supported_editors_avg_w1.append({"x": count, "y":  elem['supported_editors_avg_w1'], "z": elem["revision"]})
        weighted_reciprocity.append({"Revision": count, "Value":  elem2/float(max_reciprocity), "Wikipedia Revision": elem["revision"], "Metric":  "Reciprocity"})
        
        bipolarity.append({"Revision": count, "Value":  elem['bipolarity'], "Wikipedia Revision": elem["revision"], "Metric":  "Bipolarity"})
        wikigini.append({"Revision": count, "Value":  elem['wikigini'], "Wikipedia Revision": elem["revision"], "Metric":  "Authorship Gini"})
        deletion_weight.append({"Revision": count, "Value":  elem['deletion_weight']/float(max_total_negative_actions), "Wikipedia Revision": elem["revision"], "Metric":  "Number of Disagreement Actions (Normalized)"})
        count = count + 1
        
    
        
    #serie1  = {"key" : "No. Distinct Editors in w (w=20)", "values": distinct_editors}
    #serie2  = {"key" : "Ratio of edges between editors in w (w=20) ", "values": deletion_edges_contributors_w, "disabled": "true"}
    #serie3  = {"key" : "Ratio of sender nodes in w (w=20)", "values": deletion_outgoing_ratio, "disabled": "true"}
    #serie4  = {"key" : "Ratio of receiver nodes in w (w=20)", "values": deletion_incoming_ratio, "disabled": "true"}
    #serie5  = {"key" : "Negative reciprocity", "values": deletion_reciprocity, "disabled": "true"}
    #serie6  = {"key" : "Avg. edge weight in w (w=20)", "values": deletion_weight_avg, "disabled": "true"}
    #serie7  = {"key" : "Avg. antagonized editors in w (w=20)", "values": antagonized_editors_avg_w1, "disabled": "true"}
    #serie8  = {"key" : "Avg. supported editors in w (w=20)", "values": supported_editors_avg_w1, "disabled": "true"}
    #serie9  = {"key" : "Bipolarity", "values": bipolarity}
    
    
    #finalStats.extend(deletion_reciprocity)
    finalStats.extend(deletion_weight)
    finalStats.extend(weighted_reciprocity)
    finalStats.extend(bipolarity)
    finalStats.extend(wikigini)
    #finalStats.update({'revisions' : [serie1, serie2, serie3, serie4, serie5, serie6, serie7, serie8, serie9]})
    return "curve = " + str(finalStats) + ";"   
    

def printGraphD3(stats):   
    
    window = 50
    X_CENTRE = 500
    Y_CENTRE = 200#300
    X_UNIT = 700
    Y_UNIT = 1000 #1000
    AREA = 1050
    ZERO = 100
    AUTHOR_Y_AREA = 800
    
    colors_file = open("colors.txt", "r")
    colors_svg = colors_file.readlines()
    
    random.seed(2)
    random.shuffle(colors_svg)
    #print "colors", colors_svg
    nodes_dict = {}
    print "graph={"
    
    count = 0
    reciprocal_scores = []
    for elem in stats:
        
        (A, nodes, authDist, totalWords) = elem['adjacency_matrix']
        R = elem['reciprocity_matrix'] 
        W = elem['weight_matrix']
        C = elem['context']
        antagonistic_focus_avg = elem['antagonistic_focus_avg']
        v_str = []
        e_str = []
        individual_reciprocal_scores = []
        
        if (len(nodes) > 0):
            
            # Compute eigenvalues and eigenvectors.
            eigenvalues, eigenvectors = np.linalg.eig(A)
            
            # Compute the two minimal (negative) eigenvalues.
            copy_eigenvalues = eigenvalues.copy()
            lambda_min = min(eigenvalues)
            copy_eigenvalues[np.argmin(eigenvalues)] = float("inf")
            lambda_min_prime = min(copy_eigenvalues)

            
            # Compute eigenvectors associated to the minimal eigenvalues.
            x = eigenvectors[:,np.argmin(eigenvalues)]
            y = eigenvectors[:,np.argmin(copy_eigenvalues)]            
            if ((lambda_min < 0) and (lambda_min_prime < 0)):
                y = y * (lambda_min_prime/lambda_min)
            
            # Update nodes: editors.
            i = 0
            for node in nodes:
                
                stroke = "#fff"

                # Get the coordinates from the eigenvectors.                
                x_i = x[i].real
                y_i = y[i].real  
                
                

                # Transpolate the coordinates.
                x_i = min(X_CENTRE + (x_i * X_UNIT), X_CENTRE * 2)
                y_i = min(Y_CENTRE + (y_i * Y_UNIT), Y_CENTRE * 2)
                
                # Avoid nodes going out of the screen.
                x_i = max(x_i, ZERO)
                y_i = max(y_i, ZERO)

                # Assign a color to the node.
                if node not in nodes_dict.keys():
                    nodes_dict.update({node : len(nodes_dict) +1 })               
                group = colors_svg[nodes_dict[node] % len(colors_svg)].rstrip()

                # Compute radio of nodes w.r.t. authorship.
                if (node in authDist.keys()):
                    author_words = authDist[node]
                else:
                    author_words = 0
                v_ratio = author_words / float(totalWords)
                    
                # Mark the author node with black border. 
                if (node == elem["author"]):
                    stroke = "#000"
                
                # Add the node to the JSON structure.
                if (len(nodes)==1):
                    x_i = X_CENTRE
                    y_i = Y_CENTRE
                    v_str.append("{\"name\": \"" + node + "\", \"prop\": \"" + str(author_words) + "\", \"group\": \"" + str(group) + "\", \"x\": " + str(x_i) + ", \"y\":" + str(y_i) + ", \"value\": \"" + str(v_ratio) + "\", \"stroke\": \"" + str(stroke) + "\", \"fixed\": true}")
                #elif (x[i].real == 0 and y[i].real == 0):
                elif (x_i == X_CENTRE and y_i == Y_CENTRE and sum(A[i])==0):         
                    v_str.append("{\"name\": \"" + node + "\", \"prop\": \"" + str(author_words) + "\", \"group\": \"" + str(group) + "\", \"x\": " + str(random.randint(100, AREA)) + ", \"y\":" + str(640) + ", \"value\": \"" + str(v_ratio) + "\", \"stroke\": \"" + str(stroke) + "\", \"fixed\": true}")
                else:
                    v_str.append("{\"name\": \"" + node + "\", \"prop\": \"" + str(author_words) + "\", \"group\": \"" + str(group) + "\", \"x\": " + str(x_i) + ", \"y\":" + str(y_i) + ", \"value\": \"" + str(v_ratio) + "\", \"stroke\": \"" + str(stroke) + "\", \"fixed\": true}")
                    
                i = i + 1
                
                
            # Update nodes: authors.
            stroke = "#fff"
            for node in authDist.keys():
                
                # Select authors that are not editors.
                if node not in nodes:
                   
                    # Set the coordinates.
                    x_i = random.randint(100, AREA)
                    y_i = random.randint(100, AREA)
                    
                    # Assign a color to the node.
                    if node not in nodes_dict.keys():
                        nodes_dict.update({node : len(nodes_dict) +1 })               
                    group = colors_svg[nodes_dict[node] % len(colors_svg)].rstrip()
                    
                    # Compute radio of nodes w.r.t. authorship.
                    author_words = authDist[node]
                    v_ratio = author_words / float(totalWords)
                    
                    if (count>=window):
                        v_str.append("{\"name\": \"" + node + "\", \"prop\": \"" + str(author_words) + "\", \"group\": \"" + str(group) + "\", \"x\": " + str(x_i) + ", \"y\":" + str(AUTHOR_Y_AREA) + ", \"value\": \"" + str(v_ratio) + "\", \"stroke\": \"" + str(stroke) + "\", \"fixed\": true}")
                    else:
                        v_str.append("{\"name\": \"" + node + "\", \"prop\": \"" + str(author_words) + "\", \"group\": \"" + str(group) + "\", \"x\": " + str(x_i) + ", \"y\":" + str(y_i) + ", \"value\": \"" + str(v_ratio) + "\", \"stroke\": \"" + str(stroke) + "\", \"fixed\": true}")
                    
                    
                
            # Update links.
            i = 0
            j = 0
            
            for i in range(0, len(A)):
                for j in range(i, len(A)):
                    if (A[i][j] > 0):
                        weight = A[i][j]
                        
                        #weight = math.log(W[i][j] + W[j][i])
                        
                            
                        # Check if reciprocity.
                        if ((i, j) in R.keys()) and ((j, i) in R.keys()):
                            
                            #reciprocity = min(R[(i, j)], R[(j, i)])

                            # OLD (naive) version of reciprocity. 
                            #reciprocity_percentage = ((2.0*reciprocity)/float(W[i][j] + W[j][i]))
                            
                            # 
                            reciprocity_percentage = (min(W[i][j], W[j][i]) / float(max(W[i][j], W[j][i]))) * 0.5
                            aux = (sum(antagonistic_focus_avg[(i,j)]) + sum(antagonistic_focus_avg[(j,i)])) / float(len(antagonistic_focus_avg[(i,j)]) + len(antagonistic_focus_avg[(j,i)])) * 0.5
                            
                            #if count == 105:
                            #    print "reciprocity_percentage", reciprocity_percentage, "aux", aux
                                 
                            reciprocity_percentage = reciprocity_percentage + aux
                            
                            individual_reciprocal_scores.append((W[i][j]+W[j][i])*reciprocity_percentage)
                            #reciprocal_scores.append({reciprocity_percentage)
                            
                            contextstats = contextStats(W, C, i, j, reciprocity_percentage)
                            e_str.append("{\"source\":" + str(i) + ", \"target\":" + str(j) + ", \"value\": \""+ str(weight) + "\", \"stroke\": \"" + str("#B51404") + "\", \"opacity\": \"" + str(reciprocity_percentage+0.10) + "\", \"context\": \"" + contextstats +  contextToStr(C,i,j, nodes[i], nodes[j]) +  "\"}")
                        else:
                            contextstats = contextStats(W, C, i, j, 0)
                            e_str.append("{\"source\":" + str(i) + ", \"target\":" + str(j) + ", \"value\": \""+ str(weight) + "\", \"stroke\": \"" + str("#999") + "\", \"opacity\": \"" + str("0.55") + "\", \"context\": \"" + contextstats+  contextToStr(C,i,j,nodes[i], nodes[j])  + "\"}")
                        
                        #e_str.append("{\"source\": \"" + source + "\", \"target\": \"" + target + "\", \"value\":"+ str(weight) + "}")
                   
            
            print "" + str(count) + "" + " : {" + "\"nodes\": [" + ','.join(v_str) + "], \"links\": [" + ','.join(e_str)  + "]" + ", \"revision\": \"" + str (elem['revision'])+  "\"},"
            count = count + 1
            
    	if (len(individual_reciprocal_scores) > 0):
            reciprocal_scores.append(np.mean(individual_reciprocal_scores))
        else:
            reciprocal_scores.append(0)
        
    print "};"            
                    
    colors_file.close()        
             
    return reciprocal_scores

def contextToStr(C, i, j, name_i, name_j):
    
    context_str = "<table class='table'>"
    revs = []
    
    if (i,j) in C.keys():
        revs.extend(C[(i,j)])
    
    if (j,i) in C.keys():
        revs.extend(C[(j,i)])
    
    revs.sort()
    
    if ((i,j) in C.keys() and (j,i) in C.keys()):
        context_str = context_str + "<tr>"
        context_str = context_str + "<td width=50%>Actions from <b>" + name_i + "</b> to <b>" + name_j + "</b></td>" 
        context_str = context_str + "<td width=50%>Actions from <b>" + name_j + "</b> to <b>" + name_i + "</b></td>" 
        context_str = context_str + "</tr>"
        
    elif (i,j) in C.keys():
        context_str = context_str + "<tr>"
        context_str = context_str + "<td width=50%>Actions from <b>" + name_i + "</b> to <b>" + name_j + "</b></td>" 
        context_str = context_str + "<td width=50%></td>" 
        context_str = context_str + "</tr>"
        
    else:
        context_str = context_str + "<tr>"
        context_str = context_str + "<td width=50%>Actions from <b>" + name_j + "</b> to <b>" + name_i + "</b></td>" 
        context_str = context_str + "<td width=50%></td>"
        context_str = context_str + "</tr>"
        
    for rev_id in revs:
        
        context_str = context_str + "<tr>"
        if ((i,j) in C.keys() and (j,i) in C.keys()):
            if (rev_id in C[(i,j)].keys()):
                context_str = context_str + "<td>" + "<br /><br />".join(C[(i,j)][rev_id]) + "</td><td></td>"
            if (rev_id in C[(j,i)].keys()):
                context_str = context_str + "<td></td><td>" + "<br /><br />".join(C[(j,i)][rev_id]) + "</td>"
        elif (i,j) in C.keys():
            context_str = context_str + "<td>" + "<br /><br />".join(C[(i,j)][rev_id]) + "</td><td></td>"
        else:
            context_str = context_str + "<td>" + "<br /><br />".join(C[(j,i)][rev_id]) + "</td><td></td>"
        context_str = context_str + "</tr>"
                
    context_str = context_str + "</table>"
    return context_str

def contextStats(W, C, i, j, reciprocity_percentage):
    
    w = int(W[i][j]) + int(W[j][i])
    neg = "<b>Number of disagreement actions:</b> " + str(w) + "<br />"
    rec = "<b>Reciprocity score:</b> " + str(reciprocity_percentage) + "<br />"
    
    r = 0
    if (i,j) in C.keys():
        r = r + len(C[(i,j)])
    if (j,i) in C.keys():
        r = r + len(C[(j,i)])
        
    revs = "<b>Number of revisions where actions took place:</b> " + str(r) + "<br /><br />"
    
    return neg + rec + revs
    
    
    pass
    
    #return Cij   
def main(my_argv):
    inputfile = ''
    graph = None
    gtype = None
    edge = None 

    if (len(my_argv) <= 3):
        try:
            opts, _ = getopt.getopt(my_argv,"i:",["ifile=",])
        except getopt.GetoptError:
            print 'Usage: wikigraph.py -i <inputfile> [-g <graph>]'
            exit(2)
    else:
        try:
            opts, _ = getopt.getopt(my_argv,"i:t:e:g:",["ifile=", "type=", "edge=", "graph="])
        except getopt.GetoptError:
            print 'Usage: wikigraph.py -i <inputfile> -t <type_of_graph> -e <type_of_edge> [-g <graph>]'
            exit(2)
    
    for opt, arg in opts:
        if opt in ('-h', "--help"):
            print "wikigraph"
            print
            print 'Usage: wikigraph.py -i <inputfile> [-g <graph>]'
            print "-i --ifile File to analyze"
            print "-t --type Type of graph (d3, neo4j)"
            print "-e --edge Edge to visualize"
            print "-g --name of the article. If not specified, the parameter i is taken."
            print "-h --help This help."
            exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-g", "--graph"):
            graph = arg
        elif opt in ("-e", "--edge"):
            edge = arg
        elif opt in ("-t", "--type"):
            gtype = arg
         
    return (inputfile,gtype, edge, graph)

if __name__ == '__main__':

    (file_name, gtype, edge, graph_name) = main(argv[1:])
    
    #print "Calculating authorship for:", file_name 
    #time1 = time()
    #v, e, graph = getTimeGraph(file_name)
    statsData = getGraph(file_name)
    
    
    if (gtype == "neo4j"):
        #printForNeo4J(graph_name, v,e)
        pass
    elif (gtype == "d3"):
        reciprocity = printGraphD3(statsData)
        print printStats(statsData, reciprocity)
        
        #printForD3(v, e, edge)
        #printTimeForD3(v, e, edge, graph)
        #printSnapshotsForD3(v, e, edge, graph)
        #pass
    else:
        print "Type of graph not supported"
    #print e
    #pprint printStats(stats)
