import React from 'react';
import { Box, Typography, Portal } from '@mui/material';
import TouchAppIcon from '@mui/icons-material/TouchApp';

const ScreensaverOverlay = ({ onExit, temperature, status }) => {
  const ringColor = status ? "#B71C1C" : "#757575";
  const animated = status;

  return (
    <Portal>
      <Box
        onClick={onExit}
        onTouchStart={onExit}
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'black',
          zIndex: 99999, // resta alto per sicurezza
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#333',
          textAlign: 'center',
        }}
      >
        {/* Cerchi animati */}
        <Box
          sx={{
            position: "absolute",
            width: 400,
            height: 400,
            border: `2px dashed ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse1 9s ease-in-out infinite" : "none",
            top: "calc(50% - 200px)",
            left: "calc(50% - 200px)"
          }}
        />
        <Box
          sx={{
            position: "absolute",
            width: 370,
            height: 370,
            border: `3px dotted ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse2 6s ease-in-out infinite" : "none",
            top: "calc(50% - 185px)",
            left: "calc(50% - 185px)"
          }}
        />
        <Box
          sx={{
            position: "absolute",
            width: 340,
            height: 340,
            border: `4px solid ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse3 3s ease-in-out infinite" : "none",
            top: "calc(50% - 170px)",
            left: "calc(50% - 170px)"
          }}
        />

        {/* Contenuto */}
        <Box
          sx={{
            position: "absolute",
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography variant="h1" sx={{ fontSize: "150px" }} pl={3}>
            {temperature !== null ? `${Math.round(temperature)}°` : "--"}
          </Typography>
        </Box>

        <Typography
          variant="h6"
          sx={{
            opacity: 1,
            background: "#000",
            padding: 1,
            position: 'absolute',
            bottom: 20,
            borderTop: `1px solid #222`
          }}
        >
          <TouchAppIcon /> Touch to exit screensaver
        </Typography>

        <Box
          component="img"
          src="/Logo_ginger.svg"
          alt="Logo Ginger"
          sx={{
            position: 'fixed',
            bottom: 16,
            right: 16,
            width: "8vw",
            maxWidth: 100,
            height: 'auto',
            opacity: 0.5,
            pointerEvents: 'none'
          }}
        />
      </Box>
    </Portal>
  );
};

export default ScreensaverOverlay;
