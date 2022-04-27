import React, { useEffect, useState } from 'react'
import BasicCard from './common/BasicCard'
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import MoneyIcon from '@mui/icons-material/Money';
import WorkOutlineIcon from '@mui/icons-material/WorkOutline';
import { Box } from '@mui/system';
import { Divider, Typography } from '@mui/material';
import { Outlet, useNavigate } from 'react-router-dom';
import UploadFile from './common/UploadFile';
import TaxEquity from './TaxEquity';

// const tax = {
//     title: 'Trades Capital Gains',
//     category: 'stocks',
// }

const tabsList = [
    {
        label:'equity',
    },
    {
        label:'others'
    }
]

function LinkTab(props) {
    return (
      <Tab
        component="a"
        onClick={(event) => {
          event.preventDefault();
        }}
        {...props}
      />
    );
  }

  
const Tax = () => {

    let navigate = useNavigate();
    

    return (
        <>

            <div>
                <Box sx={{ display: 'flex', alignItems:'center', paddingY:4}}>
                    <WorkOutlineIcon fontSize='small'/>
                    <Typography variant="h6" sx={{mx:1}}>
                        Tax P&L
                    </Typography>
                </Box>
                {/* <Divider orientation='horizontal' /> */}
                <TaxEquity />
            </div>
        </>
    )
}

export default Tax