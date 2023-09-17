from typeclasses.e_room import ExtendedRoom


class Room(ObjectParent, ExtendedRoom):

    room.add_desc("Die Leere. Du befindest dich im Nichts!"
              "$state(empty, It is completely empty)"
              "$state(full, It is full of people).", room_state=("summer","empty"))