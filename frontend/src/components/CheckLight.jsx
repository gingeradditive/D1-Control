import { Box, Tooltip } from '@mui/material';
import LocalFireDepartmentIcon from '@mui/icons-material/LocalFireDepartment';
import AirIcon from '@mui/icons-material/Air';
import AlarmOffIcon from '@mui/icons-material/AlarmOff';
import AlarmIcon from '@mui/icons-material/Alarm';
import CloudSyncIcon from '@mui/icons-material/CloudSync';

export default function CheckLight({ heaterOn, fanOn, timerSet, valveOpen }) {
  return (
    <Box display="flex" justifyContent="end" alignItems="center">


      {/* Timer Icon */}
      {/* TODO: riabilitare quando verrà implementata la funzione del timer */}
      {/* <Tooltip title={timerSet ? "Timer set" : "No timer set"}>
        {timerSet ? (
          <AlarmIcon fontSize="medium" sx={{ color: '#009688', marginRight: 2 }} />
        ) : (
          <AlarmOffIcon fontSize="medium" sx={{ color: '#cccccc', marginRight: 2 }} />
        )}
      </Tooltip> */}

      {/* Heater Icon */}
      <Tooltip title={heaterOn ? "Heater ON" : "Heater OFF"}>
        <LocalFireDepartmentIcon
          fontSize="medium"
          sx={{ color: heaterOn ? '#f44336' : '#cccccc', marginRight: 2 }}
        />
      </Tooltip>

      {/* Fan Icon */}
      <Tooltip title={fanOn ? "Fan ON" : "Fan OFF"}>
        <AirIcon
          fontSize="medium"
          sx={{ color: fanOn ? '#3f51b5' : '#cccccc', marginRight: 2 }}
        />
      </Tooltip>

      {/* Valve Icon */}
      <Tooltip title={valveOpen ? "Valve Open" : "Valve Closed"}>
        <CloudSyncIcon
          fontSize="medium"
          sx={{ color: valveOpen ? '#0277BD' : '#cccccc'}}
        />
      </Tooltip>
    </Box>
  );
}
