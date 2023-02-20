Install Scripts:
Drag the _INSTALL_meta_body_ctrl.py file into your Maya viewport. Files will be copied and Meta Body Ctrl button will be added to the open shelf in Maya. 

Trouble installing? Try dragging the script into the viewport with an empty shelf open. Otherwise try the manual installation instructions http://www.madguru.com/support

Usage:
Using the Metahuman source file you exported from Bridge, click the button to create your control rig. It will not run if your character is referenced in or has a namespace. You don't really want to create a rig on a scene like that. Create the controls on your unreferenced file, then use that rig file, referenced into shots files. Animate and enjoy.

change log:
v01.13 Added metahuman tags for use with mgTools (http://www.madguru.com/mgtools) as well as space switching IK limb pole vectors controlled by an attribute on the hand and foot ctrl.
v01.12 Added a check to load the lookdevKit plugin if not already loaded. Added some code to bring the Metahuman character and scene to Y up after creating the control rig.
v01.11 corrected ik limbs issue (they were not locking in place previously, due to a problem introduced in previous update).
v01.10: Removed some hand setup parts that were causing thumb flipping.
v01.09: Removed some extra parts of rig under the hood and switched some connections to direct connections instead of constraints for performance improvements.
v01.08: Added metacarpal controls.
v01.07: Added IK toe twist control. Adjusted IK FK limbs to not shift when switching. Added IK toe rotate control.
v01.06: Added face controls labels and IKFK Matching script. Made channels keyable.
v01.05: Added toe controls and changed order of constraint creation to work with Maya 2020 and later. Added parts to allow IK FK switching with the included script. Various user friendly adjustments to channel box access.
v01.04: Adjusted ik control constraint
v01.03: IK FK controls are now hidden based on whether a limb is set to IK or FK. The foot ik controls now have an attribute for foot roll including a bend limit angle and toe straight angle. The roll attribute will let you easily rock the foot heel, ball to toe. FK foot has a toe control added. 
v01.02: Added Hand Controls with finger curl and spread. Updated to support Maya 2022 and still be backwards compatible to 2018.
v01.01: IK fix. Script checks for existing rig in scene and asks if you want to delete it before creating a new one.
v01: Initial Version

Thanks.

support@madguru.com
http://www.madguru.com/metahuman/