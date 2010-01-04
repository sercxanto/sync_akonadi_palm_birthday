#!/usr/bin/python
#
#    sync_akonadi_palm_birthday.py
#
#    Copies birthday custom field on palm to akonadi
#
#    Copyright (C) 2010 Georg Lutz <georg AT NOSPAM georglutz DOT de>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import optparse
import os
import re
import stat
import sys
import time
import types
import MySQLdb

VERSIONSTRING = "0.1"

def replaceOrAddVCardHeader(vcard, header, value):
    """Adds or replaces (if already available) vcard header"""
    vcardnew = ""
    regex = "^" + header + ":(.*)$"
    result = re.search(regex, vcard, re.MULTILINE)
    linesep = ""
    if type(result) == types.NoneType:
	# Add header after BEGIN:VCARD
	linesep ="\r\n"
	pos = vcard.find("BEGIN:VCARD" + linesep)
	if pos == -1 :
	    linesep = "\n"
	    pos = vcard.find("BEGIN:VCARD" + linesep)
	    if pos == -1:
		return vcard
	vcardnew =  vcard[0:pos+len("BEGIN:VCARD"+linesep)]
	vcardnew += header + ":" + value + linesep
	vcardnew += vcard[pos+len("BEGIN:VCARD"+linesep):]
    else:
	# Group 0 contains the whole match, not just the part in parenthesis
	line = result.group(0).strip("\r\n")
	vcardnew = vcard.replace("\n" + line, "\n" + header + ":" + value)
    return vcardnew


def copyBirthday(vcard, birthdayFieldPalm, birthdayFormat):
    """Copies birthday data from vcard birthdayField to BDAY field. Returns true if vcard was actually altered."""
    posBeginVcard = vcard.find("BEGIN:VCARD")
    if posBeginVcard == -1:
	return False, ""
    regex = "^" + birthdayFieldPalm + ":(.*)$"
    result = re.search(regex, vcard, re.MULTILINE)
    if type(result) == types.NoneType or len(result.groups()) != 1:
	# There is no palm birthday information
	return False, ""

    # Strip both - CRLF - if its there, just in case
    dateString = result.group(1).strip("\r\n")
    try:
	datePalm = datetime.datetime.strptime(dateString, birthdayFormat)
    except:
	print "Cannot convert date %s" % ( dateString )
	# There is palm birthday information, but we cannot distill a valid date out of it
	return False, ""

    # Check if we need to set BDAY field actually
    setBday = True
    result = re.search("^BDAY:(.*)$", vcard, re.MULTILINE)
    if type(result) != types.NoneType and len(result.groups()) == 1:
	# There is already a BDAY field in vcard, check if dates match
	date = datetime.date.min
	dateString = result.group(1).strip("\r\n")
	try:
	    date = datetime.datetime.strptime(dateString, "%Y-%m-%d")
	except:
	    try:
		date = datetime.datetime.strptime(dateString, "%Y-%m-%dT00:00:00")
	    except:
		pass
	if datePalm == date:
	    setBday = False

    if not setBday:
	return False, ""

    vcardnew = replaceOrAddVCardHeader(vcard, "BDAY", datePalm.strftime("%Y-%m-%d"))
    vcardnew = replaceOrAddVCardHeader(vcardnew, "REV", datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

    return True, vcardnew


########### MAIN PROGRAM #############

parser = optparse.OptionParser(
	usage="%prog [options]",
	version="%prog " + VERSIONSTRING + os.linesep +
	"Copyright (C) 2010 Georg Lutz <georg AT NOSPAM georglutz DOT de")

parser.add_option("-d", "--dateformat",
		  dest="dateformat", default="%Y-%m-%d",
		  help="Date format of palm custom field, strftime syntax. Defaults to %Y-%m-%d")
parser.add_option("-f", "--field",
		  dest="field", default="X-KPILOT-CUSTOM0",
		  help="Palm custom VCard field name, e.g. \"X-KPILOT-CUSTOM0\"")
parser.add_option("-s", "--socket",
		  dest="socket",
		  default= os.path.expanduser("~/.local/share/akonadi/db_misc/mysql.socket"),
		  help="Path to akonadi mysql socket file. Defaults to ~/.local/share/akonadi/db_misc/mysql.socket")
parser.add_option("-w", "--write",
                  action="store_true", dest="write", default=False,
                  help="Actually write changes to database (defaults to false)")

(options, args) = parser.parse_args()


try:
    fileInfo = os.stat(options.socket)
except:
    print "Socket file not found: %s" % (options.socket)
    sys.exit(1)

if not stat.S_ISSOCK(fileInfo.st_mode):
    print "No Socket file: %s" % (options.socket)
    sys.exit(1)

db = MySQLdb.connect(unix_socket=options.socket,db="akonadi")

queryString = """SELECT pimitemtable.id, pimitemtable.rev, parttable.id, parttable.data FROM parttable, pimitemtable, mimetypetable WHERE mimetypetable.id=pimitemtable.mimeTypeId AND mimetypetable.name="text/directory" AND pimitemTable.id=parttable.pimItemId""";

try:
    db.query(queryString);
except:
    print "The following query returned an error: %s" % (queryString)
    db.close()
    sys.exit(1)
r = db.store_result()

entries=r.fetch_row(maxrows=0)

if len(entries) <= 0:
    print "Didn't find any entries"
    sys.exit(0)

print "Found %d adressbook entries" % (len(entries))


i = 0
for entry in entries:
    pimitemtableId = entry[0]
    pimitemtableRev = entry[1]
    parttableId = entry[2]
    vcard = entry[3]

    copySucc, vcardnew = copyBirthday(vcard, options.field, options.dateformat)
    if copySucc:
	i+=1
	size = len(vcardnew)
	if options.write:
	    print "Changed the following entry:"
	else:
	    print "Would change the following entry:"
	print "----------------------------"
	print vcardnew
	print "------------------------------"
	print ""
	print ""
	if options.write:
	    cursor = db.cursor()
	    queryString = "UPDATE pimitemtable SET rev=%s, datetime=%s, atime=%s, dirty=%s, size=%s WHERE id=%s"
	    # interestingly datetime is utc, while atime is local time when stored in kontact
	    cursor.execute(queryString, (pimitemtableRev+1, time.strftime("%Y-%m-%d %H-%M-%S", time.gmtime()), datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"), True, size, pimitemtableId) )
	    queryString = "UPDATE parttable SET data=%s, dataSize=%s WHERE pimItemId=%s"
	    cursor.execute(queryString, (vcardnew, size, parttableId) )
	    cursor.close()
	    db.commit()

if options.write:
    print "Changed %d entries out of %d" % (i, len(entries))
else:
    print "Would have changed %d entries out of %d" % (i, len(entries))


db.close()
