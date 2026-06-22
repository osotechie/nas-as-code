#!/bin/bash
#Purpose = Restore Docker Container Data
#Version 1.0
#START

FILENAME=NAS-Backup.tar.gz                    # Define Backup file name
DES_DIR=/mnt/storage/backups/nas              # Destination of backup file


#Backup Container data
echo 'Restoring persistant data for Containers'
tar xvzf $DES_DIR/$FILENAME -C / 

#END
