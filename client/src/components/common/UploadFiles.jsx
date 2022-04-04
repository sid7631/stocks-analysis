import { Box, Typography } from '@mui/material';
import React, { useEffect, useRef, useState } from 'react'
import UploadService from "../../services/upload-files.service";
import AddFilesIcon from '../../assets/add-files.svg'
import LinearProgress from '@mui/material/LinearProgress';


const UploadFiles = (props) => {

    const [selectedFiles, setselectedFiles] = useState(undefined)
    const [currentFile, setcurrentFile] = useState(undefined)
    const [progress, setprogress] = useState(0)
    const [message, setmessage] = useState("")
    const [loading, setloading] = useState(false)

    const inputFile = useRef(null)

    const selectFile = (event) => {
        setselectedFiles(event.target.files)
        setprogress(0)
    }

    useEffect(() => {
        if (selectedFiles) {
            upload()
        }

        return () => {
            // second
        }
    }, [selectedFiles])


    const upload = () => {
        setloading(true)
        let currentFile = selectedFiles[0];

        setprogress(0)
        setcurrentFile(currentFile)

        UploadService.upload(currentFile, (event) => {
            setprogress(Math.round((100 * event.loaded) / event.total))
        })
            .then((response) => {
                setmessage(response.data.message)
                // setprogress(0)
                setloading(false)
                props.cb(response.data)
            })
            .catch((error) => {
                console.log(error)
                setprogress(0)
                setmessage("Could not upload the file!")
                setcurrentFile(undefined)
                setloading(false)
            });
        setselectedFiles(undefined)
    }

    const onButtonClick = () => {
        // `current` points to the mounted file input element
        inputFile.current.click();
    };

    return (
        <>

            <Box onClick={onButtonClick}>
                {props.children}
            </Box>

            <label className="btn btn-default">
                <input type="file" hidden onChange={selectFile} ref={inputFile} />
            </label>

            {/* <button
                className="btn btn-success"
                disabled={!selectedFiles}
                onClick={upload}
            >
                Upload
            </button> */}


            <div className="alert alert-light" role="alert">
                {message}
            </div>

            {loading ? (
                <Box sx={{ width: '20%', mt:1}}>
                    {/* <LinearProgress variant="buffer" value={progress} valueBuffer={progress+10} /> */}
                    <LinearProgress />
                </Box>
            ) : (
                <Typography variant='body1' gutterBottom >
                    {props.labelIdle}
                </Typography>

            )}
        </>
    )
}

export default UploadFiles