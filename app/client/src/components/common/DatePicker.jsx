import * as React from 'react';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import AdapterDateFns from '@mui/lab/AdapterDateFns';
import LocalizationProvider from '@mui/lab/LocalizationProvider';
import TimePicker from '@mui/lab/TimePicker';
import DateTimePicker from '@mui/lab/DateTimePicker';
import DesktopDatePicker from '@mui/lab/DesktopDatePicker';
import MobileDatePicker from '@mui/lab/MobileDatePicker';
import { Box } from '@mui/material';

export default function DatePicker(props) {
  const [value, setValue] = React.useState(null);

  const handleChange = (newValue) => {
    setValue(newValue);
    props.cb(props.label,newValue)
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
        <MobileDatePicker
          label={props.label}
          inputFormat="dd-MM-yyyy"
          value={value}
          onChange={handleChange}
        //   onAccept={handleChange}
          renderInput={(params) => <TextField size="small" {...params} />}
        />
    </LocalizationProvider>
  );
}
