        self.logger.debug("Fetching mp3 files to transcribe.")
        gh = GDriveHelper()
        mp3_folder_gdriveID = self.settings.gdrive_mp3_folder_id
        mp3_file_list = await gh.list_files_in_folder(mp3_folder_gdriveID)
        for mp3_file in mp3_file_list: