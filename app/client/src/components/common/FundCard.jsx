import * as React from 'react';
import Card from '@mui/material/Card';
import CardActions from '@mui/material/CardActions';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import { Paper, Box, Typography, Skeleton, Stack, Avatar } from '@mui/material'
import { blue, grey, blueGrey } from '@mui/material/colors';
import UtilService from '../../services/util.service';
import IconButton from '@mui/material/IconButton';
import Fingerprint from '@mui/icons-material/Fingerprint';
import Chip from '@mui/material/Chip';
import InsightsIcon from '@mui/icons-material/Insights';

const FundCard = (props) => {
  return (
    <Paper variant="outlined" sx={{ paddingY: 2, paddingX: 2 }}>
      <React.Fragment>
      <Stack direction='row' spacing={2} justifyContent='space-between' alignItems='center' mb={1} >
        {/* <Typography sx={{ fontSize: 14 }} color="text.secondary" gutterBottom>
          Equity
        </Typography> */}
        <Chip label="Equity" size="small"/>
        <IconButton aria-label="fingerprint" color="primary" onClick={() => props.action(props.data?.isin)}>
          <InsightsIcon />
        </IconButton>
      </Stack>
        <Stack sx={{ minHeight: 50 }} direction='row' spacing={2} alignItems='center'>
          <Avatar
            alt="Remy Sharp"
            src="/static/images/avatar/1.jpg"
            sx={{ width: 32, height: 32 }}
          />
          <Typography variant="body2" component="div">
            {props.data?.name}
          </Typography>
        </Stack>
        <Stack direction='row' justifyContent={'space-between'} spacing={0} marginTop={1}>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Invested</Typography>
            <Typography variant="button" component="div">{UtilService.numberFormat(props.data?.invested)}</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Current</Typography>
            <Typography variant="button" component="div">{UtilService.numberFormat(props?.data.value)}</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Returns</Typography>
            <Typography variant="button" component="div">{UtilService.numberFormat(props?.data.profit)}</Typography>
          </Box>
        </Stack>

      </React.Fragment>
    </Paper>
  );
}

export default FundCard