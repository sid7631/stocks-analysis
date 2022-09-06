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
import moment from 'moment'

const TransactionCard = (props) => {
  return (
    <Paper variant="outlined" sx={{ paddingY: 2, paddingX: 2 }}>
      <React.Fragment>
        <Stack sx={{ minHeight: 50 }} direction='row' spacing={2} justifyContent='space-between' alignItems='center'>
          <Typography variant="body2" component="div">
            Folio: {props.data?.folio}
          </Typography>
          <Box justifyItems='flex-end'>

            <Chip label={props.data?.order_type?.value} size="small" />
          </Box>
        </Stack>
        <Stack direction='row' justifyContent={'space-between'} spacing={0} marginTop={1}>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Invested Date</Typography>
            <Typography variant="button" component="div">{moment(parseInt(props.data?.date)).format("DD-MM-YYYY")}</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Units</Typography>
            <Typography variant="button" component="div">{props?.data.units}</Typography>
          </Box>
          <Box display={'flex'} flexDirection='column'>
            <Typography variant="caption" color={grey[500]} component="div">Amount</Typography>
            <Typography variant="button" component="div">{UtilService.numberFormat(props?.data.amount)}</Typography>
          </Box>
        </Stack>

      </React.Fragment>
    </Paper>
  );
}

export default TransactionCard