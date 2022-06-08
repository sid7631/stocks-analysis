import * as React from 'react';
import { Box, Typography } from '@mui/material'
import PropTypes from 'prop-types';
import { styled } from '@mui/system';
import { buttonUnstyledClasses } from '@mui/base/ButtonUnstyled';
import TabUnstyled, { tabUnstyledClasses } from '@mui/base/TabUnstyled';


import TabsUnstyled from '@mui/base/TabsUnstyled';
import TabsListUnstyled from '@mui/base/TabsListUnstyled';
import TabPanelUnstyled from '@mui/base/TabPanelUnstyled';
import { blue , grey, blueGrey } from '@mui/material/colors';

export const Tab = styled(TabUnstyled)`
  font-family: IBM Plex Sans, sans-serif;
  color: ${grey[700]};
  cursor: pointer;
//   font-size: 0.875rem;
//   font-weight: bold;
  background-color: ${grey[200]};
//   width: 100%;
//   padding: 12px 16px;
  margin-right: 12px;
//   border: none;
//   border-radius: 5px;
  display: flex;
  justify-content: center;
  outline:none;
  line-height:unset;
  letter-spacing: unset;
    text-transform: unset;


//   &:hover {
//     background-color: ${blue[700]};
//     outline:none;
//   }

  &:focus {
    color: #fff;
    outline:none;
  }

  &.${tabUnstyledClasses.selected} {
    background-color: ${blue[900]};
    color: ${blue[50]};
    outline:none;
  }

  &.${buttonUnstyledClasses.disabled} {
    opacity: 0.5;
    cursor: not-allowed;
    outline:none;
  }
`;

export const TabsList = styled(TabsListUnstyled)`
  min-width: 320px;
//   background-color: ${blue[500]};
  border-radius: 8px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  align-content: space-between;
`;
