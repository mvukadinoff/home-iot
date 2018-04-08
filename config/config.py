import configparser
import os
import hashlib



class Config:
    def __init__(self):
        self.cfg = configparser.ConfigParser()

        self.conf_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'default_conf.ini')
        conf_path="/usr/local/bin/home-iot/"
        if not os.path.exists(os.path.join(conf_path, 'conf.ini')):
            try:
                if not os.path.exists(conf_path): ## create dir if it doesn't exist
                    os.makedirs(conf_path,0o777 ) ## this will fail on Windows which is fine. Exception should be ignored.
                print("INFO: This is the first run of the application - initializing a persistant configuration file")
                self.cfg.read(self.conf_path)
                with open( os.path.join(conf_path, 'conf.ini') , "w") as configfile:
                    self.cfg.write(configfile)
                #Set the new config as the default path
                self.conf_path = os.path.join(conf_path, 'conf.ini')
                os.chmod(self.conf_path , 0o666)
                print("INFO: Created a persistant config file will now reload options from it "+self.conf_path)
            except Exception as e:
                print("Failed to move configuration file to "+conf_path +" this can be ignored for Windows "+ str(e))
        else:
            ## If it exists change it to the default path
            self.conf_path = os.path.join(conf_path, 'conf.ini')

        self.config_section = "Main Config"

        self.configOpt = dict()
        self.configOptID = dict()

        self.cfg.read(self.conf_path)
        self.config_items = self.cfg.items(self.config_section)
        ## initialize with empty values
        self.lock_file = ""
        self.lock_file_path = ""
        self.admin_user = ""
        self.admin_pass = ""
        self.log_level = ""
        self.script_timeout = ""
        self.watchdog_interval = ""
        self.listen_address = ""
        self.python_binary = ""

        self.rereadconf()

    def rereadconf(self):
        for index, item in enumerate(self.config_items):
            # index+1 as RGB requests to start from 1
            self.configOptID[index+1] = item[0]

        for item in self.config_items:
            self.configOpt[item[0]] = item[1]

        try:
            self.listen_address = self.configOpt["listen_address"]  # 1
            self.log_level = self.configOpt["log_level"]

        except Exception as e:
            print("Error while loading variables from config" + str(e))

    def get_sysconfig(self):
        self.rereadconf()
        return self.configOpt


    def get_conf_property(self, conf_property):
        try:
            # need to re-read config first in case something changed.
            self.cfg.read(self.conf_path)
            return self.cfg.get(self.config_section, conf_property)
        except Exception as e:
            print(str(e))
            return False

    def propertyExists(self, conf_property):
        # Try to get a property to verify that it exists in config
        try:
            self.cfg.get(self.config_section, conf_property)
            return True
        except Exception as e:
            print(str(e))
            return False

    def set_conf_property(self, conf_property, property_value):
        # Change a property's value inside config file
        self.cfg.set(self.config_section, conf_property, property_value)
        with open(self.conf_path, "wb") as configfile:
            self.cfg.write(configfile)
        self.rereadconf()


    def set_admin_pass(self, new_pass):
        # Salt and encrypt pass and then change it in config file
        salt = "1Ha7"
        pass_hash = hashlib.md5(salt + new_pass).hexdigest()
        self.cfg.set(self.config_section, "admin_pass", pass_hash)
        with open(self.conf_path, "wb") as configfile:
            self.cfg.write(configfile)

    def authenticated(self, provided_user, provided_pass):
        # Verify provided login credentials match the ones in config - with pass hash
        if self.admin_user is "":
            # Authentication is disabled in configuration file
            # LoggerSE.debug("authenticated : Authentication is disabled because admin_user in config is blank")
            return True

        salt = "1Ha7"
        pass_hash = hashlib.md5(salt + provided_pass).hexdigest()

        if self.admin_user == provided_user and self.admin_pass == pass_hash:
            return True

        else:
            return False

    def resetToFactory(self):
        # remove everything in the main section
        try:
            self.cfg.remove_section(self.config_section)
            # add the section clean
            self.cfg.add_section(self.config_section)
            self.cfg.set(self.config_section, "listen_address", "0.0.0.0")
            self.cfg.set(self.config_section, "listen_port", "5000")
            self.cfg.set(self.config_section, "log_level", "info")
            self.cfg.set(self.config_section, "python_binary", "python" )
            self.cfg.set(self.config_section, "script_timeout", "18")
            self.cfg.set(self.config_section, "watchdog_interval", "2" )
            self.cfg.set(self.config_section, "lock_file", "temp_lock_file")
            self.cfg.set(self.config_section, "lock_file_path", "/tmp/")

            print(self.get_sysconfig())

            with open(self.conf_path, "wb") as configfile:
                self.cfg.write(configfile)
        except Exception as e:
            print("SCRIPT ENGINE: EXCETPION WHILE REVERTING TO FACTORY DEFAULTS, you might need to overwrite the config file manually or reinstall")
        return True
