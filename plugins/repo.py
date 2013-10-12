#
import BroControl.plugin
import os
import git
import time

class ScottBro(BroControl.plugin.Plugin):
    def __init__(self):
        super(ScottBro, self).__init__(apiversion=1)

    def name(self):
        return "repo"

    def pluginVersion(self):
        return 1

    def commands(self):
        return [("bro", "[args]", "version control for running configuration.  repo.bro help for all options.")]

    def help(self):
        print """
 Usage: repo.bro [option]
        init : test configuration and create a new repo if none exists
        help : this message
        commit <msg> : commit the current config - note that this is automatically
                       done every time that 'install' is run.
        create-tag <tag> : create a checkpoint for the config tree which can be referred back to
        list-tag : list set of tags for config
        list-commits : list last 10 commits for configuration
        undo : revert back to the previous configuration
"""
    def testconfig(self):
        try:
             v1 = self.getGlobalOption('gitrepo')
        except KeyError:
             print " Please add 'GitRepo = 1' and optionally 'GitRepoDir = <dir>' to broctl.conf ."
             print " Default values are:"
             print "     GitRepo = 0"
             print "     GitRepoDir = {brobase}/spool/repo"

             return 0

        if v1 == 0:
             print "Please set GitRepo = 1 in broctl.conf"
             return 0
        return 1

    def setactor(self):
        # set repo actor info based on the 
        try:
            name = '"' + self.getGlobalOption('mailfrom') + '"'
        except KeyError:
            name = 'Big Brother <bro@host'

        try:
            email = self.getGlobalOption('mailto')
        except KeyError:
            email = 'bro@localhost'

        a = git.Actor(name,email)

        return a

    def printdiff(self):
        # test to see if we have diff printing set in broctl.cfg
        try:
            ret = self.getGlobalOption('printdiff')
        except KeyError:
            ret = False

        return ret

    def testrepo(self, repodir):

        # make sure that the repo direct exists
        if not os.path.exists(repodir):
            os.mkdir(repodir)
            print "   >> Repo directory does not exist-"
            print "   >> creating directory   ", repodir

        try: 
            repo = git.Repo(repodir)
        except git.exc.InvalidGitRepositoryError:
            repo = git.Repo.init(repodir)
            print "   >> Creating new repo in ", repodir

        return repo

    def filter_name(self, repo, name, initial):
        # test 'name' against unwanted files and see if the
        #  file has changed
        # -1 = error, -2 = bad dir/file, 0 = unchanged file, 1 = changed file
        ret = -1
       
        try:
            skipfiletypes = self.getGlobalOption('gitskipfiletypes')
        except KeyError:
            return ret
 
        try:
            skipdirs = self.getGlobalOption('gitskipdirs')
        except KeyError:
            return ret

        # extract file from name
        filename = (os.path.split(name))[1]
        # test for unwanted filetypes
        for ft in skipfiletypes.split():
            if filename.endswith(ft):
                #print "skip filetype ", filename, " ", ft
                return -2

        name_split = name.split('/')
        # look for base dirs
        if name.startswith('/') or name.startswith('.'):
            dir1 = name_split[1]
        else:
            dir1 = name_split[0]

        for sd in skipdirs.split():
            if dir1 == sd:
                return -2

        # finally look  to see if it is new
        if initial == False:
            cname = name.lstrip('./')
            try:
                x = (repo.heads.master.commit.tree/cname).hexsha
            except KeyError:
                print "NEW: ", cname
                return 1
            except ValueError:
                return -1
            except AttributeError:
                return -1
            return 0

        if initial == True:
            return 1

    def refresh_repo(self, gpath, repo, initial):
        
        os.chdir(gpath)
        ret = 0
        for dirpath, dirnames, filenames in os.walk('.', topdown=True):

            for f in filenames:
                joinfile = os.path.join(dirpath, f)
                if self.filter_name(repo,joinfile,initial) == 1: 
                    #print "-> Adding to repo: ", joinfile
                    repo.git.add(joinfile)
                    ret = 1
        return ret

    def initial_creation(self):
        # if variable can not be identified, bail
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # set the user based on bro config or defaults
        actor = self.setactor()

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)

        # need to figure out if the repo is new, or if we need to init it
        try:
             gpath = self.getGlobalOption('gitpath')
        except KeyError:
             print "KeyError for gitpath"
             return

        # if the repo is empty
        # do something about it...
        if len(repo.refs) == 0:
            self.refresh_repo(gpath,repo,True)
            repo.git.commit(author=actor.name, m='Initial commit for repo')
            print "-> Repo Init complete"
        else:
            print "-> Repo Init ignored, reference count > 0"
        return 0

    def commit(self, msg):
        # if variable can not be identified, bail
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # set the user based on bro config or defaults
        actor = self.setactor()

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)

        # need to figure out if the repo is new, or if we need to init it
        try:
             gpath = self.getGlobalOption('gitpath')
        except KeyError:
             print "KeyError for gitpath"
             return

        if self.refresh_repo(gpath,repo,False) == 1:
            repo.git.commit(author=actor.name, m=msg)
        print "-> Commit complete"
        return 0

    def list_tag(self):
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # set the user based on bro config or defaults
        actor = self.setactor()

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)
        tags = repo.tags

        print "   Tags:"
        for t in tags:
            print " -| ", t

    def create_tag(self, msg):
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # set the user based on bro config or defaults
        actor = self.setactor()

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)
        tags = repo.tags
        repo.create_tag(msg)
        print "-> Creating tag: ", msg
        return

    def list_commits(self):
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)
        n = 1

        for i in repo.iter_commits( repo.heads[0], max_count=10 ):
            print "-> ", n, " ", time.strftime("%a, %d %b %Y %H:%M", time.gmtime(i.committed_date)), " ", i, " ", i.message.rstrip()
            n = n + 1

        return            

    def undo(self):
        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)
        self.list_commits() 
        n = raw_input("Enter rollback number [1-10], or 'q' to skip: ")

        #if n.tolower() == "q":
        #    return
        return
        
    def cmd_custom(self, cmd, args):

        # test to see if git has been activated
        if self.testconfig() == 0:
              return
     
        if len(args) == 0:
            print " Argument needed for 'repo.bro'"
            self.help()
            return

        L = ""
        for c in args:
            L = L+c
        O = L.split()

        # parse options
        if O[0] == 'init':
            self.initial_creation()
        elif O[0] == 'help':
            self.help()
        elif O[0] == 'commit':
            # check for commit message
            msg = "Manual Commit"
            if len(O) > 1:
                msg = O[1]
            self.commit(msg)
        elif O[0] == 'create-tag':
            msg = "Create Tag"
            if len(O) > 1:
                msg = O[1]
            self.create_tag(msg)
        elif O[0] == 'list-tag':
            self.list_tag()
        elif O[0] == 'list-commits':
            self.list_commits()
        elif O[0] == 'undo':
            self.undo()
        else:
            print "-> unknown argument: ", O[0]
            self.help()

        return

    def cmd_install_post(self):
        # test to see if git has been activated
        if self.testconfig() == 0:
              return

        try:
             repodir = self.getGlobalOption('gitrepodir')
        except KeyError:
             print "KeyError for gitrepodir"
             return

        try:
             gpath = self.getGlobalOption('gitpath')
        except KeyError:
             print "KeyError for gitpath"
             return

        # test for directory home and existance of repo.  if not, create whatever is needed
        repo = self.testrepo(repodir)

        self.refresh_repo(gpath,repo,False)

        # look at what is different
        hcommit = repo.head.commit
        wdiff = repo.head.commit.diff(None,create_patch=True)

        # get commit id data
        actor = self.setactor()
        
        file_list = ""
        # this sort of deadman switch connected to the commit is a gross workaround to the
        #  fact that the /call/ out to the git bin horks for changes that have been prevously
        #  addressed.  the eexception seems to be generated somewhere that ignores my attempt
        #  to capture it...
        add_error = 0

        # deleated files
        for diff_del in wdiff.iter_change_type('D'):

            print "-> Deleting file from repo: ", diff_del.a_blob.path

            try:
                repo.git.remove(diff_del.a_blob.path)
            except git.exc.GitCommandError:
                print "-> Skipping file: ", diff_del.a_blob.path, "error condition"
                add_error = 1

            file_list = file_list + " " + (diff_del.a_blob.path).rstrip()

        if len(file_list) > 0 and add_error == 0:
            msg = '"Auto commit for file delete: ' + file_list + '"'
            repo.git.commit(author=actor.name, m=msg)
            file_list = ""
        else:
            add_error = 0

        # modified files
        for diff_mod in wdiff.iter_change_type('M'):

            print "-> Checking in modified file: ", diff_mod.a_blob.path
            if self.printdiff == True:
                print diff_mod.diff

            try:
                repo.git.add(diff_mod.b_blob.path)
            except git.exc.GitCommandError:
                print "-> Skipping file: ", diff_mod.a_blob.path, "error condition"
                add_error = 1

            file_list = file_list + " " + (diff_mod.a_blob.path).rstrip()

        if len(file_list) > 0 and add_error == 0:
            msg = '"Auto commit for file change ' + file_list + '"'
            try:
                repo.git.commit(author=actor.name, m=msg)
            except git.exc.GitCommandError:
                print "-> Skipping modify commit for: ", file_list, "error condition"
            file_list = ""
        else:
            add_error = 0

        # added files
        for diff_add in wdiff.iter_change_type('A'):

            print "-> Adding file to repo: ", diff_add.b_blob.path

            try:
                repo.git.add(diff_add.b_blob.path)
            except git.exc.GitCommandError:
                print "-> Skipping file: ", diff_add.b_blob.path, "error condition"
                add_error = 1

            file_list = file_list + " " + (diff_add.a_blob.path).rstrip()

        if len(file_list) > 0 and add_error == 0:
            msg = '"Auto commit for file add: ' + file_list + '"'
            repo.git.commit(author=actor.name, m=msg)
            file_list = ""
        else:
            add_error = 0
 
        return
