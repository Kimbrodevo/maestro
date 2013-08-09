import sys, os
import cmdln
from . import service

class MaestroCli(cmdln.Cmdln):
    """Usage:
        maestro SUBCOMMAND [ARGS...]
        maestro help SUBCOMMAND

    Maestro provides a command to manage multiple Docker containers
    from a single configuration.

    ${command_list}
    ${help_list}
    """
    name = "maestro"

    def __init__(self, *args, **kwargs):
      cmdln.Cmdln.__init__(self, *args, **kwargs)
      cmdln.Cmdln.do_help.aliases.append("h")

    @cmdln.option("-f", "--maestro_file",
                  help='path to the maestro file to use')
    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_build(self, subcmd, opts, *args):
      """Setup and start a set of Docker containers.

        usage:
            build
        
        ${cmd_option_list}
      """
      config = opts.maestro_file
      if not config:
        config = os.path.join(os.getcwd(), 'maestro.yml')

      if not config.startswith('/'):
        config = os.path.join(os.getcwd(), config)

      if not os.path.exists(config):
        sys.stderr.write("No maestro configuration found {0}\n".format(config))
        exit(1)
            
      containers = service.Service(config)
      containers.build()

      environment = opts.environment_file
      name = opts.name      
      if name:
        environment = self._create_global_environment(name)        
      else:
        environment = self._create_local_environment(opts)        

      containers.save(environment)

      print "Launched."
   

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_start(self, subcmd, opts, *args):
      """Start a set of Docker containers that had been previously stopped. Container state is defined in an environment file. 

        usage:
            start [container_name]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) > 0):
        container = args[0]

      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.start(container):
        containers.save(environment)
        print "Started."

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_stop(self, subcmd, opts, *args):
      """Stop a set of Docker containers as defined in an environment file. 

        usage:
            stop [container_name]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) > 0):
        container = args[0]

      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.stop(container):
        containers.save(environment)
        print "Stopped."

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_restart(self, subcmd, opts, *args):
      """Restart a set of containers as defined in an environment file. 

        usage:
            restart [container_name]
        
        ${cmd_option_list}
      """
      self.do_stop('stop', opts, args)
      self.do_start('start', opts, args)

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_destroy(self, subcmd, opts, *args):
      """Stop and destroy a set of Docker containers as defined in an environment file. 

        usage:
            destroy
        
        ${cmd_option_list}
      """
      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      if containers.destroy():
        containers.save(environment)
        print "Destroyed."
 
    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    @cmdln.option("-a", "--attach", action="store_true",
                  help='Attach to the running container to view output')    
    @cmdln.option("-d", "--dont_add", action="store_true",
                  help='Just run the command and exit. Don\'t add the container to the environment')        
    def do_run(self, subcmd, opts, *args):
      """Start a set of Docker containers that had been previously stopped. Container state is defined in an environment file. 

        usage:
            run template_name [commandline]
        
        ${cmd_option_list}
      """
      container = None
      if (len(args) == 0):
        sys.stderr.write("Error: Container name must be provided\n")
        exit(1)

      environment = self._verify_environment(opts)
      
      template = args[0]
      commandline = args[1:]
      print " ".join(commandline)
      containers = service.Service(environment=environment)
      containers.run(template, commandline, attach=opts.attach, dont_add=opts.dont_add) 
      containers.save(environment)

      if opts.dont_add:
        print "Execution of " + template + " complete."
      else:
        print "Adding a new instance of " + template + "."   

    @cmdln.option("-e", "--environment_file",
                  help='path to the environment file to use to save the state of running containers')
    @cmdln.option("-n", "--name",
                  help='Create a global named environment using the provided name')
    def do_ps(self, subcmd, opts, *args):
      """Show the status of a set of containers as defined in an environment file. 

        usage:
            ps
        
        ${cmd_option_list}
      """
      environment = self._verify_environment(opts)
      
      containers = service.Service(environment=environment)
      print containers.ps() 

    def _verify_global_environment(self, name):
      """
      Setup the global environment.
      """
      # Default to /var/lib/maestro and check there first
      path = '/var/lib/maestro'
      if not os.path.exists(path) or not os.access(path, os.W_OK):            
        env_path = os.path.join(path, name)
        # See if the environment exists in /var/lib maestro
        if not os.path.exists(env_path):              
          # If the environment doesn't exist or is not accessible then we check ~/.maestro instead
          path = os.path.expanduser(os.path.join('~', '.maestro'))
          if not os.path.exists(path):
            sys.stderr.write("Global named environments directory does not exist {0}\n".format(path))
            exit(1)

      env_path = os.path.join(path, name)
      if not os.path.exists(env_path):
        sys.stderr.write("Environment named {0} does not exist\n".format(env_path))
        exit(1)
      
      if not os.access(env_path, os.W_OK):
        sys.stderr.write("Environment named {0} is not writable\n".format(env_path))
        exit(1)

      return os.path.join(env_path, 'environment.yml')

    def _create_global_environment(self, name):
      """
      Setup the global environment.
      """
      # Default to /var/lib/maestro
      # It has to exist and be writable, otherwise we'll just use a directory relative to ~
      path = '/var/lib/maestro'
      if not os.path.exists(path) or not os.access(path, os.W_OK):      
        # If /var/lib/maestro doesn't exist or is not accessible then we use ~/.maestro instead
        path = os.path.expanduser(os.path.join('~', '.maestro'))
        if not os.path.exists(path):
          print "Creating ~/.maestro to hold named environments"
          os.makedirs(path)

      # The environment will live in a directory under path
      env_path = os.path.join(path, name)
      if not os.path.exists(env_path):
        print "Initializing ~/.maestro/" + name
        os.makedirs(env_path)
      return os.path.join(env_path, 'environment.yml')

    def _verify_environment(self, opts):
      """
      Verify that the provided environment file exists.
      """
      if opts.name:
        environment = self._verify_global_environment(opts.name)
      else:
        environment = self._create_local_environment(opts)        
        
        if not os.path.exists(environment):
          sys.stderr.write("Could not locate the environments file {0}\n".format(environment))
          exit(1)

        if not os.access(environment, os.W_OK):
          sys.stderr.write("Environment file {0} is not writable\n".format(environment))
          exit(1)

      return environment
    
    def _create_local_environment(self, opts):
      environment = opts.environment_file
      if not environment:
        base = os.path.join(os.getcwd(), '.maestro')  
        environment = os.path.join(base, 'environment.yml')
        if not os.path.exists(base):
          print "Initializing " + base
          os.makedirs(base)

      return environment