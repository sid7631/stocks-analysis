import React, { useEffect, useRef, useState } from 'react';

// Import React FilePond
import { FilePond, registerPlugin } from 'react-filepond';

// Import FilePond styles
import 'filepond/dist/filepond.min.css';

// Import the Image EXIF Orientation and Image Preview plugins
// Note: These need to be installed separately
// `npm i filepond-plugin-image-preview filepond-plugin-image-exif-orientation --save`
import FilePondPluginImageExifOrientation from 'filepond-plugin-image-exif-orientation';
import FilePondPluginImagePreview from 'filepond-plugin-image-preview';
import FilePondPluginFileValidateType from 'filepond-plugin-file-validate-type';
import FilePondPluginFileMetadata from 'filepond-plugin-file-metadata';
import 'filepond-plugin-image-preview/dist/filepond-plugin-image-preview.css';

// Register the plugins
registerPlugin(FilePondPluginImageExifOrientation, FilePondPluginImagePreview, FilePondPluginFileValidateType,FilePondPluginFileMetadata);

const UploadFile = (props) => {
    const myPondRef = useRef(null);
    const [files, setFiles] = useState([]);

    useEffect(function () {
        // calling setOptions
        // myPondRef.current._pond.setOptions({
        //     fileMetadataObject: {
        //         bank:props.bank,
        //         account: props.account,
        //     }
        // })
    });

    return (
        <>
            <FilePond
                ref={myPondRef}
                files={files}
                onupdatefiles={setFiles}
                allowMultiple={props.allowMultiple}
                maxFiles={props.maxFiles}
                server={props.server}
                name="file"
                credits={false}
                labelIdle={'Drag & Drop your ' + props.title + ' or <span class="filepond--label-action">Browse</span>'}
            /></>
    );
};

export default UploadFile;