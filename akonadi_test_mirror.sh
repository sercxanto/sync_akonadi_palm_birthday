#!/bin/sh
# Copies akonadis mysql database installation for test purposes to a temporary location

# folder where the script is located
abspath="$(cd "${0%/*}" 2>/dev/null; echo "$PWD"/"${0##*/}")"
dir=`dirname $abspath`
akonadi_mirror=$dir/akonadi_mirror

mypidfile=`ls $akonadi_mirror/db_data/*pid 2>/dev/null`
rc=$?
if [ $rc == 0 ]; then
    MYSQLPID=`cat "$mypidfile"  2>/dev/null `
    if [ -n "$MYSQLPID" ]; then
	/bin/kill "$MYSQLPID" >/dev/null 2>&1
    fi
fi

rm -rf $akonadi_mirror
akonadictl stop
sleep 8
cp -rp ~/.local/share/akonadi $akonadi_mirror
akonadictl start

/usr/libexec/mysqld --defaults-file=$akonadi_mirror/mysql.conf --datadir=$akonadi_mirror/db_data/ --socket=$akonadi_mirror/db_misc/mysql.socket &
