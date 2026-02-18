import React, { useEffect, useState } from "react";
import { Box, Typography, Switch, styled, Select, MenuItem, FormControl } from "@mui/material";
import WaterDropIcon from "@mui/icons-material/WaterDrop";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import DewPointIcon from '@mui/icons-material/DewPoint';
import CheckLight from './CheckLight';

const StyledSwitch = styled(Switch)(({ theme }) => ({
  width: 56.5,
  height: 34.5,
  padding: 7,
  transform: "scale(1.5)",
  "& .MuiSwitch-switchBase": {
    padding: 8,
    "&.Mui-checked": {
      transform: "translateX(22px)",
      color: "#fff",
      "& + .MuiSwitch-track": {
        backgroundColor: "green",
        opacity: 1,
      },
    },
  },
  "& .MuiSwitch-thumb": {
    backgroundColor: "#f1f1f1",
    width: 18,
    height: 18,
  },
  "& .MuiSwitch-track": {
    borderRadius: 20 / 2,
    backgroundColor: "red",
    opacity: 1,
  },
}));

export default function Footer({ ext_hum, int_hum, dew_point, status, onStatusChange, heater, fan, valve, presets = [], activePresetId, onPresetSelect }) {
  const [checked, setChecked] = useState(status);

  // Sync internal state with external prop
  useEffect(() => {
    setChecked(status);
  }, [status]);

  const handleChange = (event) => {
    const newStatus = event.target.checked;
    setChecked(newStatus);           // Update internal state
    onStatusChange(newStatus);       // Notify parent
  };

  return (
    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      p={1}
      borderRadius={2}
      mt={2}
    >
      <Box display="flex" alignItems="center">
        {presets.length > 0 && (
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select
              value={activePresetId || ''}
              onChange={(e) => {
                const preset = presets.find(p => p.id === e.target.value);
                if (preset) onPresetSelect(preset);
              }}
              displayEmpty
              sx={{ fontSize: '0.85rem', height: 36 }}
            >
              <MenuItem value="" disabled>
                <em>Use Preset</em>
              </MenuItem>
              {presets.map((preset) => (
                <MenuItem key={preset.id} value={preset.id}>
                  {preset.name} ({preset.temperature}°C)
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
      </Box>
      <Box position="relative" display="flex" justifyContent="end" alignItems="center"> 
        <CheckLight
          heaterOn={heater}
          fanOn={fan}
          timerSet={false} // TODO: implement timerSet logic
          valveOpen={valve}
        />
        <Box position="relative" display="flex" justifyContent="end" alignItems="center" ml={3}>
          <StyledSwitch checked={checked} onChange={handleChange} />
          <Box
            position="absolute"
            left={checked ? 37 : 4.5}
            top={10}
            pointerEvents="none"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <PowerSettingsNewIcon style={{ fontSize: 14, color: "gray" }} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
