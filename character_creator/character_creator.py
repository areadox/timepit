"""
Character Creator contrib, by InspectorCaracal

# Features

The primary feature of this contrib is defining the name and attributes
of a new character through an EvMenu. It provides an alternate `charcreate`
command as well as a modified `at_look` method for your Account class.

# Usage

In order to use the contrib, you will need to create your own chargen
EvMenu. The included `example_menu.py` gives a number of useful techniques
and examples, including how to allow players to choose and confirm
character names from within the menu.

"""
import string
from random import choices

from django.conf import settings

from evennia import DefaultAccount
from evennia.commands.default.muxcommand import MuxAccountCommand
from evennia.objects.models import ObjectDB
from evennia.utils import create, search, logger, utils
from evennia.utils.evmenu import EvMenu

import evennia
import time

_CHARACTER_TYPECLASS = settings.BASE_CHARACTER_TYPECLASS
try:
    _CHARGEN_MENU = settings.CHARGEN_MENU
except AttributeError:
    _CHARGEN_MENU = "evennia.contrib.rpg.character_creator.example_menu"


class ContribCmdCharCreate(MuxAccountCommand):
    """
    create a new character

    Begin creating a new character, or resume character creation for
    an existing in-progress character.

    You can stop character creation at any time and resume where
    you left off later.
    """

    key = "erschaffung"
    locks = "cmd:pperm(Player) and is_ooc()"
    help_category = "General"

    def func(self):
        "create the new character"
        account = self.account
        session = self.session

        # only one character should be in progress at a time, so we check for WIPs first
        in_progress = [chara for chara in account.db._playable_characters if chara.db.chargen_step]

        if len(in_progress):
            # we're continuing chargen for a WIP character
            new_character = in_progress[0]
        else:
            # we're making a new character
            charmax = settings.MAX_NR_CHARACTERS

            if not account.is_superuser and (
                account.db._playable_characters and len(account.db._playable_characters) >= charmax
            ):
                plural = "" if charmax == 1 else "s"
                self.msg(f"Du kannst {charmax} character{plural} haben.")
                return

            # create the new character object, with default settings
            # start_location = ObjectDB.objects.get_id(settings.START_LOCATION)
            default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
            permissions = settings.PERMISSION_ACCOUNT_DEFAULT
            # generate a randomized key so the player can choose a character name later
            key = "".join(choices(string.ascii_letters + string.digits, k=10))
            new_character = create.create_object(
                _CHARACTER_TYPECLASS,
                key=key,
                location=None,
                home=default_home,
                permissions=permissions,
            )
            # only allow creator (and developers) to puppet this char
            new_character.locks.add(
                f"puppet:pid({account.id}) or perm(Developer) or"
                f" pperm(Developer);delete:id({account.id}) or perm(Admin)"
            )
            # initalize the new character to the beginning of the chargen menu
            new_character.db.chargen_step = "menunode_welcome"
            account.db._playable_characters.append(new_character)

        # set the menu node to start at to the character's last saved step
        startnode = new_character.db.chargen_step
        # attach the character to the session, so the chargen menu can access it
        session.new_char = new_character

        # this gets called every time the player exits the chargen menu
        def finish_char_callback(session, menu):
            char = session.new_char
            if not char.db.chargen_step:
                # this means character creation was completed - start playing!
                # execute the ic command to start puppeting the character
                account.execute_cmd("spiele {}".format(char.key))

        EvMenu(session, _CHARGEN_MENU, startnode=startnode, cmd_on_exit=finish_char_callback)

class MuxAccountLookCommand(DefaultAccount):
    """
    Custom parent (only) parsing for OOC looking, sets a "playable"
    property on the command based on the parsing.

    """

    def parse(self):
        """Custom parsing"""

        super().parse()

        playable = self.account.db._playable_characters
        if playable is not None:
            # clean up list if character object was deleted in between
            if None in playable:
                playable = [character for character in playable if character]
                self.account.db._playable_characters = playable
        # store playable property
        if self.args:
            self.playable = dict((utils.to_str(char.key.lower()), char) for char in playable).get(
                self.args.lower(), None
            )
        else:
            self.playable = playable


# Obs - these are all intended to be stored on the Account, and as such,
# use self.account instead of self.caller, just to be sure. Also self.msg()
# is used to make sure returns go to the right session

# note that this is inheriting from MuxAccountLookCommand,
# and has the .playable property.
class CmdOOCLook(DefaultAccount):
    """
    look while out-of-character

    Usage:
      look

    Look in the ooc state.
    """

    # This is an OOC version of the look command. Since a
    # Account doesn't have an in-game existence, there is no
    # concept of location or "self". If we are controlling
    # a character, pass control over to normal look.

    key = "look"
    aliases = ["l", "ls","b"]
    locks = "cmd:all()"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """implement the ooc look command"""

        if self.session.puppet:
            # if we are puppeting, this is only reached in the case the that puppet
            # has no look command on its own.
            self.msg("Du kannst dich gerade nicht umschaun.")
            return

        if _AUTO_PUPPET_ON_LOGIN and _MAX_NR_CHARACTERS == 1 and self.playable:
            # only one exists and is allowed - simplify
            self.msg("Du bist gerade nicht in einem Character (OOC).\nBenutze |wspiele|n um das Spiel zu betreten.")
            return

        # call on-account look helper method
        self.msg(self.account.at_look(target=self.playable, session=self.session))


class ContribChargenAccount(DefaultAccount):
    """
    A modified Account class that makes minor changes to the OOC look
    output, to incorporate in-progress characters.
    """

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called by the OOC look command. It displays a list of playable
        characters and should be mostly identical to the core method.

        Args:
            target (Object or list, optional): An object or a list
                objects to inspect.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)
        """

        # list of targets - make list to disconnect from db
        characters = list(tar for tar in target if tar) if target else []
        sessions = self.sessions.all()
        is_su = self.is_superuser

        # text shown when looking in the ooc area
        result = [f"Account |g{self.key}|n (you are Out-of-Character)"]

        nsess = len(sessions)
        if nsess == 1:
            result.append("\n\n|wConnected session:|n")
        elif nsess > 1:
            result.append(f"\n\n|wConnected sessions ({nsess}):|n")
        for isess, sess in enumerate(sessions):
            csessid = sess.sessid
            addr = "{protocol} ({address})".format(
                protocol=sess.protocol_key,
                address=isinstance(sess.address, tuple)
                and str(sess.address[0])
                or str(sess.address),
            )
            if session.sessid == csessid:
                result.append(f"\n |w* {isess+1}|n {addr}")
            else:
                result.append(f"\n   {isess+1} {addr}")

        result.append("\n\n |whelp|n - mehr commandos")
        result.append("\n |wpublic <Text>|n - talk on public channel")

        charmax = settings.MAX_NR_CHARACTERS

        if is_su or len(characters) < charmax:
            result.append("\n |werschaffung|n - So erschaffst du einen neuen Character")

        if characters:
            result.append("\n |wloesche <name>|n - loesche einen Character (kann nicht rueckgaengig gemacht werden)")
        plural = "" if len(characters) == 1 else "s"
        result.append("\n |wspiele <character>|n - enter the game (|wooc|n to return here)")
        if is_su:
            result.append(f"\n\nVerfuegbare Character{plural} ({len(characters)}/unlimited):")
        else:
            result.append(f"\n\nVerfuegbare Character{plural} ({len(characters)}/{charmax}):")

        for char in characters:
            if char.db.chargen_step:
                # currently in-progress character; don't display placeholder names
                result.append("\n - |Yin der erschaffung|n (|werschaffung|n zum fortfahren)")
                continue
            csessions = char.sessions.all()
            if csessions:
                for sess in csessions:
                    # character is already puppeted
                    sid = sess in sessions and sessions.index(sess) + 1
                    if sess and sid:
                        result.append(
                            f"\n - |G{char.key}|n [{', '.join(char.permissions.all())}] (played by"
                            f" you in session {sid})"
                        )
                    else:
                        result.append(
                            f"\n - |R{char.key}|n [{', '.join(char.permissions.all())}] (played by"
                            " someone else)"
                        )
            else:
                # character is available
                result.append(f"\n - {char.key} [{', '.join(char.permissions.all())}]")
        look_string = ("-" * 68) + "\n" + "".join(result) + "\n" + ("-" * 68)
        return look_string


class DeuCmdCharDelete(MuxAccountCommand):
    """
    delete a character - this cannot be undone!

    Usage:
        chardelete <charname>

    Permanently deletes one of your characters.
    """

    key = "loesche"
    locks = "cmd:pperm(Player)"
    help_category = "General"

    def func(self):
        """delete the character"""
        account = self.account

        if not self.args:
            self.msg("Usage: loesche <charactername>")
            return

        # use the playable_characters list to search
        match = [
            char
            for char in utils.make_iter(account.db._playable_characters)
            if char.key.lower() == self.args.lower()
        ]
        if not match:
            self.msg("You have no such character to delete.")
            return
        elif len(match) > 1:
            self.msg(
                "Aborting - there are two characters with the same name. Ask an admin to delete the"
                " right one."
            )
            return
        else:  # one match
            from evennia.utils.evmenu import get_input

            def _callback(caller, callback_prompt, result):
                if result.lower() == "yes":
                    # only take action
                    delobj = caller.ndb._char_to_delete
                    key = delobj.key
                    caller.db._playable_characters = [
                        pc for pc in caller.db._playable_characters if pc != delobj
                    ]
                    delobj.delete()
                    self.msg(f"Character '{key}' was permanently deleted.")
                    logger.log_sec(
                        f"Character Deleted: {key} (Caller: {account}, IP: {self.session.address})."
                    )
                else:
                    self.msg("Deletion was aborted.")
                del caller.ndb._char_to_delete

            match = match[0]
            account.ndb._char_to_delete = match

            # Return if caller has no permission to delete this
            if not match.access(account, "delete"):
                self.msg("You do not have permission to delete this character.")
                return

            prompt = (
                "|rThis will permanently destroy '%s'. This cannot be undone.|n Continue yes/[no]?"
            )
            get_input(account, prompt % match.key, _callback)


class DeuCmdIC(MuxAccountCommand):
    """
    control an object you have permission to puppet

    Usage:
      spiele <character>

    Go in-character (spiele) as a given Character.

    This will attempt to "become" a different object assuming you have
    the right to do so. Note that it's the ACCOUNT character that puppets
    characters/objects and which needs to have the correct permission!

    You cannot become an object that is already controlled by another
    account. In principle <character> can be any in-game object as long
    as you the account have access right to puppet it.
    """

    key = "spiele"
    # lock must be all() for different puppeted objects to access it.
    locks = "cmd:all()"
    aliases = "puppet"
    help_category = "General"

    # this is used by the parent
    account_caller = True

    def func(self):
        """
        Main puppet method
        """
        account = self.account
        session = self.session

        new_character = None
        character_candidates = []

        if not self.args:
            character_candidates = [account.db._last_puppet] if account.db._last_puppet else []
            if not character_candidates:
                self.msg("Usage: ic <character>")
                return
        else:
            # argument given

            if account.db._playable_characters:
                # look at the playable_characters list first
                character_candidates.extend(
                    utils.make_iter(
                        account.search(
                            self.args,
                            candidates=account.db._playable_characters,
                            search_object=True,
                            quiet=True,
                        )
                    )
                )

            if account.locks.check_lockstring(account, "perm(Builder)"):
                # builders and higher should be able to puppet more than their
                # playable characters.
                if session.puppet:
                    # start by local search - this helps to avoid the user
                    # getting locked into their playable characters should one
                    # happen to be named the same as another. We replace the suggestion
                    # from playable_characters here - this allows builders to puppet objects
                    # with the same name as their playable chars should it be necessary
                    # (by going to the same location).
                    character_candidates = [
                        char
                        for char in session.puppet.search(self.args, quiet=True)
                        if char.access(account, "puppet")
                    ]
                if not character_candidates:
                    # fall back to global search only if Builder+ has no
                    # playable_characters in list and is not standing in a room
                    # with a matching char.
                    character_candidates.extend(
                        [
                            char
                            for char in search.object_search(self.args)
                            if char.access(account, "puppet")
                        ]
                    )

        # handle possible candidates
        if not character_candidates:
            self.msg("That is not a valid character choice.")
            return
        if len(character_candidates) > 1:
            self.msg(
                "Multiple targets with the same name:\n %s"
                % ", ".join("%s(#%s)" % (obj.key, obj.id) for obj in character_candidates)
            )
            return
        else:
            new_character = character_candidates[0]

        # do the puppet puppet
        try:
            account.puppet_object(session, new_character)
            account.db._last_puppet = new_character
            logger.log_sec(
                f"Puppet Success: (Caller: {account}, Target: {new_character}, IP:"
                f" {self.session.address})."
            )
        except RuntimeError as exc:
            self.msg(f"|rYou cannot become |C{new_character.name}|n: {exc}")
            logger.log_sec(
                f"Puppet Failed: %s (Caller: {account}, Target: {new_character}, IP:"
                f" {self.session.address})."
            )



class CmdWer(MuxAccountCommand):
    """
    list who is currently online

    Usage:
      wer
      doing

    Shows who is currently online. Doing is an alias that limits info
    also for those with all permissions.
    """

    key = "wer"
    aliases = "online"
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    def func(self):
        """
        Get all connected accounts by polling session.
        """
        account = self.account
        session_list = evennia.SESSION_HANDLER.get_sessions()

        session_list = sorted(session_list, key=lambda o: o.account.key)

        if self.cmdstring == "doing":
            show_session_data = False
        else:
            show_session_data = account.check_permstring("Developer") or account.check_permstring(
                "Admins"
            )

        naccounts = evennia.SESSION_HANDLER.account_count()
        if show_session_data:
            # privileged info
            table = self.styled_table(
                "|wAccount Name",
                "|wOn for",
                "|wIdle",
                "|wPuppeting",
                "|wRoom",
                "|wCmds",
                "|wProtocol",
                "|wHost",
            )
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                puppet = session.get_puppet()
                location = puppet.location.key if puppet and puppet.location else "None"
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                    utils.crop(puppet.get_display_name(account) if puppet else "None", width=25),
                    utils.crop(location, width=25),
                    session.cmd_total,
                    session.protocol_key,
                    isinstance(session.address, tuple) and session.address[0] or session.address,
                )
        else:
            # unprivileged
            table = self.styled_table("|wAccount name", "|wOn for", "|wIdle")
            for session in session_list:
                if not session.logged_in:
                    continue
                delta_cmd = time.time() - session.cmd_last_visible
                delta_conn = time.time() - session.conn_time
                session_account = session.get_account()
                table.add_row(
                    utils.crop(session_account.get_display_name(account), width=25),
                    utils.time_format(delta_conn, 0),
                    utils.time_format(delta_cmd, 1),
                )
        is_one = naccounts == 1
        self.msg(
            "|wAccounts:|n\n%s\n%s unique account%s logged in."
            % (table, "One" if is_one else naccounts, "" if is_one else "s")
        )



class CmdEnde(MuxAccountCommand):
    """
    quit the game

    Usage:
      ende

    Switch:
      all - disconnect all connected sessions

    Gracefully disconnect your current session from the
    game. Use the /all switch to disconnect from all sessions.
    """

    key = "ende"
    switch_options = ("all",)
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    def func(self):
        """hook function"""
        account = self.account

        if "all" in self.switches:
            account.msg(
                "|RQuitting|n all sessions. Hope to see you soon again.", session=self.session
            )
            reason = "quit/all"
            for session in account.sessions.all():
                account.disconnect_session_from_account(session, reason)
        else:
            nsess = len(account.sessions.all())
            reason = "quit"
            if nsess == 2:
                account.msg("|RQuitting|n. One session is still connected.", session=self.session)
            elif nsess > 2:
                account.msg(
                    "|RQuitting|n. %i sessions are still connected." % (nsess - 1),
                    session=self.session,
                )
            else:
                # we are quitting the last available session
                account.msg("|RQuitting|n. Hope to see you again, soon.", session=self.session)
            account.disconnect_session_from_account(self.session, reason)