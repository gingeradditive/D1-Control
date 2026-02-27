import React, { useEffect, useState } from "react";
import { Box, Typography, Switch, styled, Button, keyframes } from "@mui/material";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import CheckLight from './CheckLight';

const marqueeScroll = keyframes`
  0% { transform: translateX(0%); }
  50% { transform: translateX(-100%); }
  100% { transform: translateX(0%); }
`;

function MarqueeText({ text, maxChars = 8 }) {
  const needsMarquee = text.length > maxChars;
  return (
    <Box
      sx={{
        overflow: 'hidden',
        width: 88,
        display: 'flex',
        alignItems: 'center',
        justifyContent: needsMarquee ? 'flex-start' : 'center',
        position: 'relative',
      }}
    >
      <Typography
        variant="caption"
        noWrap
        sx={{
          fontSize: '0.75rem',
          fontWeight: 600,
          lineHeight: 1.2,
          whiteSpace: 'nowrap',
          ...(needsMarquee && {
            animation: `${marqueeScroll} 24s linear infinite`,
            display: 'inline-block',
            minWidth: 'max-content',
          }),
        }}
      >
        {text}
      </Typography>
    </Box>
  );
}

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

export default function Footer({ ext_hum, int_hum, dew_point, status, onStatusChange, heater, fan, valve, presets = [], pinnedPresetIds = [], activePresetId, onPresetSelect }) {
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
      <Box display="flex" alignItems="center" gap={0.75}>
        {pinnedPresetIds
          .map(id => presets.find(p => p.id === id))
          .filter(Boolean)
          .map((preset) => (
            <Button
              key={preset.id}
              variant={activePresetId === preset.id ? 'contained' : 'outlined'}
              size="small"
              onClick={() => onPresetSelect(preset)}
              sx={{
                borderRadius: '20px',
                minWidth: 94,
                maxWidth: 94,
                height: 34,
                px: 1,
                textTransform: 'none',
                border: '1px solid #ccc',
                color: '#000',
                bgcolor: '#fff',
                boxShadow: 'none',
                '&:hover': {
                  border: '1px solid #ccc',
                  bgcolor: '#f5f5f5',
                  boxShadow: 'none',
                },
                ...(activePresetId === preset.id
                  ? { bgcolor: 'rgb(215, 46, 40)', color: '#fff', border: '1px solid rgb(215, 46, 40)', '&:hover': { bgcolor: 'rgb(185, 36, 30)', border: '1px solid rgb(185, 36, 30)' } }
                  : {}
                ),
                '&.Mui-disabled': {
                  borderColor: '#fff',
                  color: '#fff',
                  bgcolor: 'transparent',
                  boxShadow: 'none',
                },
              }}
            >
              <MarqueeText text={preset.name} />
            </Button>
          ))}
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
