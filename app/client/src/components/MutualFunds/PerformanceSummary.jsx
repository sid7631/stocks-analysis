import { Paper, Box, Typography } from '@mui/material'
import React from 'react'
import { blue, grey, blueGrey } from '@mui/material/colors';

const PerformanceSummary = () => {
  return (
    <>
      <Box>
        <Paper sx={{ padding: 2, display: 'flex' }}>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="subtitle2" color={grey[500]} component="div">Current Value</Typography>
            <Typography variant="h6" component="div">₹2.06L</Typography>
            <Typography variant="subtitle2" component="div">1 Day Change ₹-2.30K ▼-1.10%</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="subtitle2" color={grey[500]} component="div">Invested</Typography>
            <Typography variant="h6" component="div">₹2.00L</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="subtitle2" color={grey[500]} component="div">Returns</Typography>
            <Typography variant="h6" component="div">₹6.69K</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="subtitle2" color={grey[500]} component="div">XIRR%</Typography>
            <Typography variant="h6" component="div">8.90%</Typography>
          </Box>
        </Paper>
      </Box>
    </>
  )
}

export default PerformanceSummary