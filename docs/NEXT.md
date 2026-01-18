# Next

## Dump Ideas and Roughly Sort in Order of Importance

Honey feeder, kibble feeder, obviously the camera for verification, feeding chime, Maybe a graph, redundancies for everything obviously, And then the dev document obviously has some pretty useful testing criteria and you know mechanisms of failure, that kind of thing.
And then we have the server side, which is kind of complicated, I guess we want multiple possible points of access, monitoring, probably a path through discord and not through discord, yeah I mean we do want like a server like a real server involved in this, because I'm doing it separate home lab kind of thing and this is a good opportunity to connect to that ... I guess that's a good start. possible points of failure so far, Benny doesn't wake up, for some reason the Libre craps out, Benny rips the Libre off while we're not there, I guess just general Libre failure. 
then there's home internet failure, so you need everything to continue working locally if the internet fails, so that would mean a redundant Libre connection to the server through Bluetooth directly. power could go out, so that would just be like a backup power to the server, it would really only have to run for few hours also it like barely does any work so it should be kind of minimal you could easily run it on like a backup power protocol where you just wake up every I don't know half hour or 15 minutes and and the you know you inspect glucose data and there and you run a more conservative heating approach.
Oh and then we obviously need the everything fails and turns off solution, which is a simple like if things turn off we release some food. like probably like a rescue and a little bit of a maintenance dose. because if everything fails like obviously he needs to eat and we you know can't monitor anymore and we just need to make sure. 
anything else? oh Momo could eat his food I guess. so preventing that probably looks like more like monitoring, I am skeptical that she would. like if Benny is awake and he hears the food and he gets up he'll probably eat it. and if he goes to eat it Momo will not go to eat it. 
yeah I guess that's fine and then eventually for quality of life it would be cool to you know uncover or release like a puzzle. Oh another point of failure is like the dogs could just somehow get into the food ahead of time. that's actually not that serious of a failure, you know something to think about. probably not something to prioritize yet. That's like a lower thing cuz like if they eat it's like well that's bad but it's not that bad it's like a you know P2 failure instead of like a P1 failure right? 

anyway cool. 

## PI Compatibility Check

Make sure the project is still capable of running on pi + pi venv cleanup

## SSH Disconnect Issue with PI

## Camera Testing

## Let's look at the dev.md
