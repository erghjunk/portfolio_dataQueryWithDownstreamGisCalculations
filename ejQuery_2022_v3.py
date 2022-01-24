"""
author: evan fedorko, evanjfedorko@gmail.com
date: 12/2019
last check: 1/2022; runs with ArcGIS Desktop 10.8.1 and whichever
antiquated version of Python (2.7 probably) that installs with that software.
also requires pandas.

the client wanted to compile environmental justice information
(as published by the EPA) for water discharging facilities in the US,
and specifically, for people living within 1 mile downstream of the discharge
this script is the ULTRA budget version of that analysis. At the time of writing
the published tools for doing this sort of analysis with NHDPlus data did not
work, or required some major hoops, so I wrote this instead. A lot of the "power"
of this analysis is wrapped up in the power of the NHD data itself.

the major weaknesses of this analysis (concessions to time/budget) are:

1. actual discharge distance is, essentially, approximated
2. EJ polygons are at a very different scale than drainage
polygons and this is entirely unaccounted for; if an EJ
polygon intersects a drainage polygon, all it's data are included
for that facility

most of this is solveable with, you guessed it, more time.
"""


from arcpy import MakeFeatureLayer_management, SearchCursor, Statistics_analysis, SelectLayerByLocation_management, CopyFeatures_management, env
import pandas as pan
from shutil import copyfile
import os, datetime, re
import time

startTime = time.time()

# Set to overwrite pre-existing files
arcpy.env.overwriteOutput = True

# source data paths, test and nat'l
ws = os.getcwd()
output = ws + r"\output.csv"

# sets default workspace for arcpy
arcpy.env.workspace = ws


# delete the old log file since we're writing in a mode
def deleteOldLog():
	try:
		os.remove(ws + r"\logging.txt")
	except OSError:
		pass

deleteOldLog()


def writeToLog(news):
    logfile = open(ws + r"\logging.txt", 'a')
    logfile.write(news)
    logfile.write('\n')
    logfile.close()
    return


def copyOutputCSV(toCopy):
	timedate = re.sub('\ |\?|\.|\!|\/|\;|\:', '', str(datetime.datetime.now().date()) + "_" + str(datetime.datetime.now().time()))
	copyfile(toCopy, ws + "output_" + timedate + ".csv")
	return


def copyLog(toCopy):
	timedate = re.sub('\ |\?|\.|\!|\/|\;|\:', '', str(datetime.datetime.now().date())+"_"+str(datetime.datetime.now().time()))
	copyfile(toCopy, ws + "log_" + timedate + ".txt")


def writeOutputFeatures(featureClass, selectionList, fieldName, outputName):
	where = fieldName + " IN (" + ', '.join(map(str, selectionList)) + ")"
	# select features
	arcpy.MakeFeatureLayer_management(featureClass, "selected_lyr", where)
	arcpy.CopyFeatures_management("selected_lyr", outputName)


writeToLog("variables read in")


def analysis():

	ws = "C:\\workspace\\programmingWorkspace\\americanRivers\\"

	# source data, etc, geodatabases
	nhdplus = ws + r"\testFeatures.gdb"
	potwDB = ws + r"\testPOTW.gdb"
	ejdb = ws + r"\EJ_Screen.gdb"
	workdb = ws + r"\working.gdb"
	gisOut = ws + r"\analysisOutputs.gdb"

	# ins, test
	flow = ws + r"\flow.csv"  # this is a table describing the sequence of flow of streams
	catch = nhdplus + r"\testCatch"  # these are drainage area catchments for stream segments
	potw = potwDB + r"\testPoint2"  # these polluting facilities
	ej = ejdb + r"\EJScreen_test"  # this is environmental justice data from the EPA
	flowline = ws + r"\localFlowlines.csv"  # these are stream segments

	# outouts/permanent and temporary
	localEj = workdb + r"\LocalEJ"
	ejStats = ws + r"\ejStats.csv"
	blankOutput = ws + r"\blankOutput.csv"
	ejList = []
	catchOutList = []
	ejOut = gisOut + r"\foundEJPolygons"
	catchOut = gisOut + r"\foundCatchPolygons"

	# make layers
	# friendly reminder:  these can be manipulated in place, so always create a copy
	# or otherwise account for this when using a method or func that does not create an output
	arcpy.MakeFeatureLayer_management(ej, "ej_lyr")

	writeToLog("layers made")

	# establish cursors (arcpy and pandas) that will be used in loop
	potwTable = arcpy.SearchCursor(potw, fields='FIRST_REGISTRY_ID; FEATUREID')
	flowTable = pan.read_csv(flow, sep=',', usecols=['FROMCOMID', 'TOCOMID'])
	flowlineTable = pan.read_csv(flowline, sep=',', usecols=['COMID', 'LENGTHKM'])

	writeToLog("cursors and data frames made")

	loop = 0

	for potw in potwTable:
		"""
		this loop navigates downstream until the sum of the lengths of the streams
		corresponding to the catchments is >= to the testLength variable
		client wants to consider 1 mile downstream (1.6 km) which is
		complicated by the fact that a POTW may be at any position within a
		catchment. this script takes 1/2 of the local length to start as a
		messy way of dealing with the issue
		"""
		length = 0.0
		testLength = 1.6
		# list of catchments that current potw flows to, starting with the
		# catchment the potw resides within
		catches = []
		# output will be written per registry ID
		potwID = potw.FIRST_REGISTRY_ID
		writeToLog("working on " + str(potwID))
		localComID = potw.FEATUREID
		catches.append(localComID)
		# "local" length
		for index, row in flowlineTable[flowlineTable.COMID == localComID].iterrows():
			length += int(row.LENGTHKM) / 2
		# reading and recording flow catches; this may fail in some flow table cases
		# it's hard to know all possiblities
		while length <= testLength:
			for index, row in flowTable[flowTable.FROMCOMID == localComID].iterrows():
				nextID = row.TOCOMID
			# this is failing if length is > testLength from the initial calculation
			catches.append(nextID)
			# this break statement will terminate the while loop
			# and move on to the writeToLog statement after the loop
			if nextID == 0:
				break
			# recalculate the length we've 'traveled'
			for index, row in flowlineTable[flowlineTable.COMID == localComID].iterrows():
				length += row.LENGTHKM
			localComID = nextID
		writeToLog("catches identified")

		for item in catches:
			if item not in catchOutList:
				catchOutList.append(item)

		# string together SQL statement for selecting the catchments
		# result of this should be "FEATUREID in (#, #, #)"
		# .join and map are neccessary to properly convert ints in a list to strings w/out 'L' appended
		where = "FEATUREID IN (" + ', '.join(map(str, catches)) + ")"
		writeToLog(where)
		# select local catchments from all catchments
		arcpy.MakeFeatureLayer_management(catch, "selected_catch_lyr", where)

		# select EJ polygons that intersect identified catchments
		arcpy.SelectLayerByLocation_management("ej_lyr", "intersect", "selected_catch_lyr")
		arcpy.CopyFeatures_management("ej_lyr", localEj)
	
		# NEW CODE HERE TO STORE LIST OF THESE IDs; IF NOT IN STYLE
		tempEJCursor = arcpy.SearchCursor(localEj, fields='ID')
		for row in tempEJCursor:
			test = row.ID
			if test not in ejList:
				ejList.append(test)

		# create summary EJ stats for that POTW
		statsFields = [["ACSTOTPOP", "SUM"], ["MINORPOP", "SUM"], ["LOWINCOME", "SUM"], ["LINGISO", "SUM"], ["UNDER5", "SUM"], ["OVER64", "SUM"]]
		arcpy.Statistics_analysis(localEj, ejStats, statsFields)
		writeToLog("stats calculated")
		# read stats and write out to file w/facility ID
		stats = pan.read_csv(ejStats)
		# set the OBJECTID field equal to the facility id; output table has one row only ([0])
		stats.at[0, 'OBJECTID'] = potwID
		# create a new output file each time we run it, overwriting the old one
		if loop == 0:
			copyfile(blankOutput, output)
		# append line to output file
		with open(output, 'a') as f:
			stats.to_csv(f, header=False)
			f.close()
		writeToLog("output written for " + str(potwID))
		loop += 1

	# select and save all EJ polygons and catchments here using:	
	# writeOutputFeatures(featureClass, selectionList, fieldName, outputName)
	# but first, re-write EJ list with '' around each item 
	ejList2 = []
	for num in ejList:
		new = "'" + str(num) + "'"
		ejList2.append(new)

	writeOutputFeatures(ej, ejList2, "ID", ejOut)
	writeOutputFeatures(catch, catchOutList, "FEATUREID", catchOut)


# main program
analysis()
# copy the CSV we were appending to
copyOutputCSV(output)
# last write to log
writeToLog('The script took {0} seconds.'.format(time.time() - startTime))
# copy log
copyLog(ws + r"\logging.txt")
