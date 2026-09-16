## RHS[L] Auto Fisher
Be sure to mute the in-game music, increase the Roblox volume, and mute all other audio sources playing on your computer.

## Download
Download the latest `AutoFisher.exe` from the
[Releases page](../../releases/latest)

Note: Windows may flag the .exe as unrecognized, click **'More info' → 'Run anyway'** to run it. 

## Settings
- **Threshold:** RMS volume level that counts as "sound detected" (0.0–1.0). If the program is not detecting audio, try lowering this volume/increasing your Roblox volume. If the program is clicking multiple times per fish, increase this value. 
- **Chunk Size:** Samples read per audio chunk
- **Sample Rate:** Audio sample rate (Hz)
- **Cooldown:** Minimum time between sound-triggered clicks
- **Click Delay:** Delay between the two clicks of a double-click
- **Silence Timeout:** Seconds of silence before auto re-casting (it's best to keep this it's default value)

Watch the live RMS readout in the GUI while your game is silent vs. when the
sound cue plays, and set the threshold somewhere in between.
