# House of Misfits Weeping Willow

Weeping Willow is a custom bot developed for the House of Misfits mental health server. 

It consists of a modular WeepingWillowClient, as well as custom modules.

## How the modules work

When `houseofmisfits.weeping_willow.WeepingWillowClient` is first loaded, it looks in 
`.modules.__module_list__` for the names of modules it needs to register.

A `Module` is really just a collection of `Triggers`. A `Trigger` pairs a value from a
Discord event (such as an incoming message) with a callable. For example, `ChannelTrigger`
runs an action whenever a message comes in on a specific channel.

The module currently only reacts to message events. Further development is needed to 
respond to other kinds of events, such as DMs or emoji reactions.