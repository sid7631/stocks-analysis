import React, { useEffect } from 'react'
import { Paper, Box, Typography, Skeleton, Stack } from '@mui/material'
import { blue, grey, blueGrey } from '@mui/material/colors';
import MutualFundService from '../../services/mutual-fund.services';
import { useState } from 'react';
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import Grid from '@mui/material/Unstable_Grid2';

import UtilService from '../../services/util.service';
import FundCard from '../common/FundCard';
import { Outlet, useNavigate } from 'react-router-dom';


const PerformanceSummary = () => {

  const [summary, setsummary] = useState(null)
  const [performance, setperformance] = useState([])
  const [funds, setfunds] = useState([])
  const [loading, setloading] = useState(false)
  let navigate = useNavigate();

  useEffect(() => {

    setloading(true)
    MutualFundService.getPerformance().then(response => {
      setsummary(response.data.summary)
      setperformance(response.data.performance)
      setfunds(response.data.funds)
      setloading(false)
    }).catch(error => {
      console.log(error)
      setloading(false)
    })

    return () => {
      // second
    }
  }, [])

  const cardAction = (param) => {
    navigate(param)
  }


  return (
    <>
      {loading ? (

        <Box sx={{ width: '100%' }}>
          <Skeleton />
          <Skeleton animation="wave" />
          <Skeleton animation={false} />
        </Box>
      ) : (

        <>
          <Box sx={{ flexGrow: 1 }}>
            <Grid container spacing={2}>

              <Grid xs={12}>
                <Box sx={{ marginBottom: 2 }}>
                  <Typography>Portfolio Performance</Typography>
                </Box>
                <Box>
                  <Stack direction='row' justifyContent={'space-between'} spacing={0} marginBottom={2}>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Current Value</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.value)}</Typography>
                      <Typography variant="subtitle2" component="div">Invested {UtilService.numberFormat(summary?.invested)}</Typography>
                    </Box>
                    <Box display={'flex'} flexDirection='column'>
                      <Typography variant="subtitle2" color={grey[500]} component="div">Returns</Typography>
                      <Typography variant="h6" component="div">{UtilService.numberFormat(summary?.total_return)}</Typography>
                      <Typography variant="subtitle2" component="div">1 Day Change ₹ {UtilService.numberFormat(summary?.day_change)} ▼{summary?.day_change_perc}%</Typography>
                    </Box>
                  </Stack>
                </Box>
                <HighchartsReact
                  highcharts={Highcharts}
                  constructorType={"stockChart"}
                  options={{
                    rangeSelector: {
                      selected: 4
                    },

                    title: {
                      text: '',
                    },

                    scrollbar: {
                      enabled: false,
                    },

                    tooltip: {
                      formatter() {
                        let s = '<b>' + Highcharts.dateFormat('%b %e, %Y', this.x) + '</b>';

                        this.points.forEach(point => {
                          s += '<br/>Portfolio : ' + UtilService.numberFormat(point.y);
                        });

                        return s;
                      }
                    },

                    series: [{
                      name: 'Portfolio',
                      data: performance,
                    }],
                    credits: {
                      enabled: false
                    }
                  }}
                />
              </Grid>
              <Grid xs={12}>
                <Box sx={{ marginBottom: 2 }}>
                  <Typography>My Mutual Funds</Typography>
                </Box>
                <Grid container spacing={2}>
                  {funds.map((item, index) => (
                    <Grid item xs={12} sm={6} md={4} lg={3} key={index} >
                      <FundCard  data={item} action={cardAction}></FundCard>
                    </Grid>
                  ))}

                </Grid>


              </Grid>
            </Grid>
          </Box>
        </>
      )}
    </>
  )
}

export default PerformanceSummary


