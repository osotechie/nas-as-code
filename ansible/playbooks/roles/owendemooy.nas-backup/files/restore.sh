#!/bin/bash
#Purpose = Restore Docker Container Data
#Version 1.0
#START

DES_DIR=/docker                           		# Location of Data to be backed up
SRC_DIR=/mnt/storage/backups/nas-repo       	# Destination of backup file

export RESTIC_PASSWORD=

echo $(date)'   Starting Restore'
echo $(date)'   -----------------------------------------------------------------------------------'

#Restore Container data
echo $(date)'    Restoring persistant data for Containers from backup'
echo restic -r $SRC_DIR --verbose restore latest --target $DES_DIR
restic -r $SRC_DIR --verbose restore latest --target $DES_DIR

#END
