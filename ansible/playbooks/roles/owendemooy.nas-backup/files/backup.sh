#!/bin/bash
#Purpose = Backup Docker Container Data
#Version 1.0
#START

LVM_VG=ubuntu-vg		         		 # Define name of the LVM Group to create snapshot from
LVM_LV=$LVM_VG/ubuntu-lv                 # Define name of the LVM Volume to create snapshot from
SNAPSHOT=BACKUP                          # Name for the Snapshot (note: cannot use SNAPSHOT as resevered word)
SNAPSHOT_SIZE=100G			 			 # Size to allocate for Snapshot
SNAPSHOT_DEV=/dev/$LVM_VG/$SNAPSHOT 	 # Device path to the snapshot
SNAPSHOT_MNT=/mnt/backup/snapshot	 	 # Mount point for the snapshot

FILENAME=NAS-Backup.tar.gz               # Define Backup file name
SRC_DIR=docker                           # Location of Data to be backed up
DES_DIR=/mnt/storage/backups/nas         # Destination of backup file
STACKS=/config/stacks			 		 # Define path to dir containing subdirs for each docker stack

EXCLUDE_DIR="$SRC_DIR/media/plex/Library/Application Support/Plex Media Server/Cache"

echo $(date)'   Starting Backup'
echo $(date)'   -----------------------------------------------------------------------------------'
echo $(date)"   Excluded Directories: $EXCLUDE_DIR"

#Stop Docker Containers to allow clean backup
echo $(date)'    Stopping Container'
for dir in $STACKS/*/; do
	cd "$dir"
	docker compose stop
	cd ..
done

#Create Snapshot to backup data from
echo $(date)'    Creating Snapshot'
lvcreate -s -n $SNAPSHOT -L $SNAPSHOT_SIZE $LVM_LV
mount $SNAPSHOT_DEV $SNAPSHOT_MNT

#Re-start Docker Containers now we have a snapshot to work from
for dir in $STACKS/*/; do
	cd "$dir"
	docker compose up -d
	cd ..
done

#Backup data
echo $(date)'    Backing up persistant data for Containers'
echo tar --exclude="$EXCLUDE_DIR" -cpzf $DES_DIR/$FILENAME -C $SNAPSHOT_MNT $SRC_DIR
tar --exclude="$EXCLUDE_DIR" -cpzf $DES_DIR/$FILENAME -C $SNAPSHOT_MNT $SRC_DIR

#Remove snapshot
echo $(date)'    Removing Snapshot'
umount $SNAPSHOT_MNT
lvremove $LVM_VG/$SNAPSHOT -f

#Unmount external cifs share
#echo $(date)'    Unmounting Backup Share'
#umount $DES_DIR

#END

