# -*- coding: utf-8 -*-
"""
Connection screen

This is the text to show the user when they first connect to the game (before
they log in).

To change the login screen in this module, do one of the following:

- Define a function `connection_screen()`, taking no arguments. This will be
  called first and must return the full string to act as the connection screen.
  This can be used to produce more dynamic screens.
- Alternatively, define a string variable in the outermost scope of this module
  with the connection string that should be displayed. If more than one such
  variable is given, Evennia will pick one of them at random.

The commands available to the user when the connection screen is shown
are defined in evennia.default_cmds.UnloggedinCmdSet. The parsing and display
of the screen is done by the unlogged-in "look" command.

"""

from django.conf import settings

from evennia import utils

CONNECTION_SCREEN = """
  /###           /                                  ##### ##                   
 /  ############/ #                              ######  /###     #            
/     #########  ###                            /#   /  /  ###   ###     #     
#     /  #        #                            /    /  /    ###   #     ##     
 ##  /  ##                                         /  /      ##         ##     
    /  ###      ###   ### /### /###     /##       ## ##      ## ###   ######## 
   ##   ##       ###   ##/ ###/ /##  / / ###      ## ##      ##  ### ########  
   ##   ##        ##    ##  ###/ ###/ /   ###   /### ##      /    ##    ##     
   ##   ##        ##    ##   ##   ## ##    ### / ### ##     /     ##    ##     
   ##   ##        ##    ##   ##   ## ########     ## ######/      ##    ##     
    ##  ##        ##    ##   ##   ## #######      ## ######       ##    ##     
     ## #      /  ##    ##   ##   ## ##           ## ##           ##    ##     
      ###     /   ##    ##   ##   ## ####    /    ## ##           ##    ##     
       ######/    ### / ###  ###  ### ######/     ## ##           ### / ##     
         ###       ##/   ###  ###  ### ##### ##   ## ##            ##/   ##    
                                            ###   #  /                         
                                             ###    /                          
                                              #####/                           
                                                ###                            
|b==============================================================|n
 Willkommen in der |g{}|n, version {}!
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)


CONNECTION_SCREEN_2 = """
88888888888 d8b                        8888888b.  d8b 888    
    888     Y8P                        888   Y88b Y8P 888    
    888                                888    888     888    
    888     888 88888b.d88b.   .d88b.  888   d88P 888 888888 
    888     888 888 "888 "88b d8P  Y8b 8888888P"  888 888    
    888     888 888  888  888 88888888 888        888 888    
    888     888 888  888  888 Y8b.     888        888 Y88b.  
    888     888 888  888  888  "Y8888  888        888  "Y888 
                                                                                  
|b==============================================================|n
 Willkommen in der |g{}|n, version {}!
|b==============================================================|n""".format(
    settings.SERVERNAME, utils.get_evennia_version("short")
)
