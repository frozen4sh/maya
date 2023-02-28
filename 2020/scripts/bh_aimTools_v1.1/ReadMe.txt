Thank you for purchasing bh_aimTools, I hope it helps you do great animation.
Please do not share this, I am a solo freelance animator who invests a good bit of time developing
these tools. Cheers, Brian


To Install :

Put the script in your Maya>Scripts folder and restart Maya.

Type (in the MEL field) :

source "bh_aimTools.mel";

and hit enter to launch the GUI. For convenience this command can be added to a 
shelf button (icon is provided).


To Use :

Select a control on your rig and press 'Create Aim Locator'
That will create and select the locator, move it to a suitable place to aim at 
(I find this easier is the move tool is set to 'local' mode).

Once you are satisfied with the positioning, select the locator (NB not the control!)
and press 'Attach Locator To Control'. With this you have the option to attach 
only on existing keys on the control ('KeysOnly' checkbox checked) or all frames
in the time slider with that unchecked. Experiment to see which works best for your shot.

Confirm the locator is following the control as you want it to by playing the timeline
Then press 'Aim control At Locator' to apply the aim constraint - (NB Again you ONLY need to
select the locator - this is a simpler/faster workflow than the typical constraint
workflow in Maya.

You'll notice there's an extra locator created after doing this, it's purely a visual guide to show
the twist axis for the control - rotate the Aim Locator in that axis to twist as needed.

Now you can adjust the animation in your preferred methods, Motion trails work great here - since
you are just tracking a locator in world space there's very little slowdown using them. Animation layers 
are also great to add to the locator to make changes when there are a lot of keys on it.

If at any time you don't like the changes you've made simply delete the locator and start again.

Once you are happy with the animation changes using the Aim Locator select it again and press
'Key Control From Aim Locator' to transfer the animation back to the control. Again here you have the 
option to key only on the existing keys on the locator or all frames in the timeline. Experiment to see
which works best for you (Undo should get you back to previous state if it doesn't suit).

Repeat for as many controls as needed.. 

To see a demo of how this tool might be used to help speed up the process of adding overlap please see
this video : https://vimeo.com/314845542


