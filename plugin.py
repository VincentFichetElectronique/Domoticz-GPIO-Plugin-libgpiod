# Domoticz-GPIO-Plugin libgpiod
#
# Authors: Dnpwwo, Domcars0
# Contribs : V.Fichet
#
#
"""
<plugin key="RaspberryPiGPIO" name="Raspberry Pi GPIO (libgpiod)" author="Adapted" version="2.0.0">
    <description>
        <h2>Domoticz GPIO Plugin</h2><br/>
        <h3>Configuration</h3>
        <ul style="list-style-type:square">
            <li style="line-height:normal">Output GPIO Pins - Comma delimited list of output (relay) GPIO pins. Format is pin number colon NC|NO|TO colon 0|1  ( e.g 16:TO:1, for GPIO16 where TO is for "On/Off" Button, NO is "Push On" Button, NC is a "Push Off" Button. 1 means active_low switch, 0 means active_high switch ) </li>
            <li style="line-height:normal">Input GPIO Pins - Comma delimited list of board GPIO pin (e.g 2 for GPIO2, 14 for GPIO14, ...) to check for input</li>
            <li style="line-height:normal">Heartbeat Frequency - Determines how often Input Pins are checked for values in seconds</li>
            <li style="line-height:normal">Debug - When true the logging level will be much higher to aid with troubleshooting</li>
        </ul>
		To delete a device created by this plugin just delete the ouput/input pins in the comma separated list.
    </description>
    <params>
        <param field="Mode1" label="Outputs GPIO BCM (ex: 5:TO:0,17:TO:1)" width="250px" required="false" default=""/>
        <param field="Mode2" label="Inputs GPIO BCM (ex: 22,23)" width="250px" required="false" default=""/>
        <param field="Mode3" label="Inputs internal bias" width="250px">
            <options>
                <option label="Pull-Up (idle to 3,3V / contact to GND)" value="PULL_UP" default="true"/>
                <option label="Pull-Down (idle to GND / contact to 3.3V)" value="PULL_DOWN"/>
                <option label="Aucun (résistance externe)" value="DISABLED"/>
            </options>
        </param>
        <param field="Mode4" label="Heartbeat Frequency (sec)" width="75px" required="true" default="1"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""
import os
import Domoticz
import gpiod
from gpiod.line import Direction, Value, Bias


class BasePlugin:
    def __init__(self):
        self.gpio_request = None
        self.outputs = {}   # {bcm: active_level} (0 ou 1)
        self.inputs = []    # [bcm1, bcm2, ...]
        self.unit_map = {}  # {bcm: UnitID}
        self.bias_mode = "PULL_UP"

    def get_chip_path(self):
        if os.path.exists("/dev/gpiochip4"):
            return "/dev/gpiochip4"
        return "/dev/gpiochip0"

    def get_bias_setting(self):
        if self.bias_mode == "PULL_UP":
            return Bias.PULL_UP
        elif self.bias_mode == "PULL_DOWN":
            return Bias.PULL_DOWN
        return Bias.DISABLED

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)

        self.bias_mode = Parameters["Mode3"]
        line_config = {}
        unit_idx = 1

        # 1. Analyse des sorties (ex: "5:TO:0,17:TO:1" ou "5:0" ou "5:NC")
        raw_out = Parameters["Mode1"].strip()
        if raw_out:
            for item in raw_out.split(","):
                parts = [p.strip().upper() for p in item.split(":")]
                bcm = int(parts[0])
                
                # Détection du niveau logique actif (1 par défaut, 0 si :0 ou :NC)
                active_level = 1
                if len(parts) >= 3 and parts[2] in ("0", "NC", "LOW"):
                    active_level = 0
                elif len(parts) == 2 and parts[1] in ("0", "NC", "LOW"):
                    active_level = 0

                self.outputs[bcm] = active_level
                self.unit_map[bcm] = unit_idx

                # État initial au démarrage = OFF (donc inverse de active_level)
                init_val = Value.ACTIVE if active_level == 0 else Value.INACTIVE
                line_config[bcm] = gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=init_val
                )
                if unit_idx not in Devices:
                    Domoticz.Device(Name=f"Sortie GPIO {bcm}", Unit=unit_idx, TypeName="Switch", Used=1).Create()
                unit_idx += 1

        # 2. Analyse des entrées (ex: "22,23")
        raw_in = Parameters["Mode2"].strip()
        if raw_in:
            bias_setting = self.get_bias_setting()
            for item in raw_in.split(","):
                bcm = int(item.strip())
                self.inputs.append(bcm)
                self.unit_map[bcm] = unit_idx

                line_config[bcm] = gpiod.LineSettings(
                    direction=Direction.INPUT,
                    bias=bias_setting
                )
                if unit_idx not in Devices:
                    Domoticz.Device(Name=f"Entrée GPIO {bcm}", Unit=unit_idx, TypeName="Switch", Used=1).Create()
                unit_idx += 1

        # 3. Ouverture des lignes via libgpiod
        if line_config:
            chip = self.get_chip_path()
            Domoticz.Log(f"libgpiod sur {chip} | Sorties (niveau actif): {self.outputs} | Entrées: {self.inputs}")
            self.gpio_request = gpiod.request_lines(
                chip,
                consumer="domoticz-gpio",
                config=line_config
            )

        freq = max(1, int(Parameters["Mode4"]))
        Domoticz.Heartbeat(freq)
        self.read_inputs(force_update=True)

    def onStop(self):
        if self.gpio_request:
            self.gpio_request.release()
            self.gpio_request = None

    def onCommand(self, Unit, Command, Level, Hue):
        target_bcm = None
        for bcm, u_id in self.unit_map.items():
            if u_id == Unit and bcm in self.outputs:
                target_bcm = bcm
                break

        if target_bcm is None or not self.gpio_request:
            return

        active_level = self.outputs[target_bcm]
        turn_on = (Command == "On")

        if turn_on:
            val = Value.ACTIVE if active_level == 1 else Value.INACTIVE
        else:
            val = Value.INACTIVE if active_level == 1 else Value.ACTIVE

        self.gpio_request.set_value(target_bcm, val)
        n_val = 1 if turn_on else 0
        s_val = "On" if turn_on else "Off"
        Devices[Unit].Update(nValue=n_val, sValue=s_val)

    def read_inputs(self, force_update=False):
        if not self.gpio_request or not self.inputs:
            return

        for bcm in self.inputs:
            u_id = self.unit_map[bcm]
            raw_val = self.gpio_request.get_value(bcm)

            if self.bias_mode == "PULL_UP":
                is_active = (raw_val == Value.INACTIVE)
            else:
                is_active = (raw_val == Value.ACTIVE)

            n_val = 1 if is_active else 0
            s_val = "On" if is_active else "Off"

            if force_update or Devices[u_id].nValue != n_val:
                Devices[u_id].Update(nValue=n_val, sValue=s_val)

    def onHeartbeat(self):
        self.read_inputs(force_update=False)


global _plugin
_plugin = BasePlugin()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onCommand(Unit, Command, Level, Hue):
    _plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
    _plugin.onHeartbeat()
