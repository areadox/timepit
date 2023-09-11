from commands.command import Command
from evennia import CmdSet

class CmdEcho(Command):
    """
    Ein echo kommando

    Benutze es so:
        echo <deine Eingabe>

    """
    key = "echo"

    def func(self):
        self.caller.msg(f"Echo: {self.args.strip()}")

class CmdSpielerBuch(Command):
    """
    Ein echo kommando

    Benutze es so:
        echo <deine Eingabe>

    """
    key = "spielerbuch"
    aliases = ["sp"]

    def func(self):
        self.caller.msg("""
+-----------------------------------------------------------------------------+
|Name: {name:20}                                                   |
+-----------------------------------------------------------------------------+
|  Staerke  :{sta:3d}           Intelligenz :{int:3d}          Weissheit :{wei:3d}           |
|  Ausdauer :{ausd:3d}           Vitalitaet  :{vit:3d}          konsentrazion :{kons:3d}     |
|
        """.format(sta=self.caller.staerke,
        int=self.caller.intelligenz, 
        wei=self.caller.weissheit,
        ausd=self.caller.ausdauer,
        vit=self.caller.vitalitaet,
        kons=self.caller.konsentrazion,
        name="name string"))






class CmdNimm(Command):
    """
    
    Nimm etwas auf

    """

    key = "nimm"
    aliases = ["nehmen", "aufheben"]
    locks = "cmd:all();view:perm(Developer);read:perm(Developer)"
    arg_regex = r"\s|$"

    def func(self):
        """implements the command."""

        caller = self.caller

        if not self.args:
            caller.msg("Nimm was?")
            return
        obj = caller.search(self.args, location=caller.location)
        if not obj:
            return
        if caller == obj:
            caller.msg("Du kannst Dich nicht selber nehmen.")
            return
        if not obj.access(caller, "get"):
            if obj.db.get_err_msg:
                caller.msg(obj.db.get_err_msg)
            else:
                caller.msg("Du kannst das nicht nehmen.")
            return

        # calling at_pre_get hook method
        if not obj.at_pre_get(caller):
            return

        success = obj.move_to(caller, quiet=True, move_type="get")
        if not success:
            caller.msg("Das kann man nicht aufheben.")
        else:
            singular, _ = obj.get_numbered_name(1, caller)
            caller.location.msg_contents(f"$You() nimmt {singular}.", from_obj=caller)
            # calling at_get hook method
            obj.at_get(caller)


class DeuCmdSet(CmdSet):

    def at_cmdset_creation(self):
        self.add(CmdEcho)
        self.add(CmdNimm)
        self.add(CmdSpielerBuch)