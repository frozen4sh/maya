const fs = require('fs');
const https = require('https');
const { promisify } = require('util');
const path = require('path');
const { exec } = require('child_process');
const kidsnoteData = require('./kidsnote.json');

const writeFileAsync = promisify(fs.writeFile);
const renameAsync = promisify(fs.rename);
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// 이미지파일 다운로드
const downloadImage = (url) => {
  return new Promise((resolve, reject) => {
    const tempFilename = `temp-${Math.random().toString(36).substring(2, 15)}-${Date.now()}.jpg`;
    const fileStream = fs.createWriteStream(tempFilename);
    https.get(url, (response) => {
      if (response.statusCode === 200) {
        response.pipe(fileStream);
        fileStream.on('finish', () => {
          fileStream.close(() => resolve(tempFilename));
        });
      } else {
        fileStream.close(() => fs.unlink(tempFilename, () => {}));
        reject(new Error(`Failed to download ${tempFilename}, status code: ${response.statusCode}`));
      }
    }).on('error', (err) => {
      fs.unlink(tempFilename, () => {});
      reject(err);
    });
  });
};

const processImage = async (url, finalFilename, content, retries = 5) => {
  try {
    // 파일명에 한글이 포함되지 않도록 임시 파일명을 사용하여 이미지를 다운로드
    const tempFilename = await downloadImage(url);
    // 한글 파일명으로 파일명 변경
    await renameAsync(tempFilename, finalFilename);
    console.log(`Renamed ${tempFilename} to ${finalFilename}`);
  } catch (error) {
    console.log(`Error processing ${finalFilename}: ${error.message}`);
    if (retries > 0) {
      console.log(`Retrying ${finalFilename}. Retries left: ${retries}`);
      await sleep(5000); // 5초 기다린 후 재시도
      await processImage(url, finalFilename, content, retries - 1);
    }
  }
};


const processEntries = async () => {
  for (const entry of kidsnoteData.results) {
    const { date_written, class_name, child_name, content, weather, attached_images } = entry;
    const formattedDate = date_written.replace(/-/g, '년') + '일';
    const comment =`${formattedDate}(${weather}\n${content}`;
    if (attached_images && attached_images.length > 0) {
      for (const image of attached_images) {
        const finalFilename = `${formattedDate}-${class_name}-${child_name}-${image.id}.jpg`;
        await processImage(image.original, finalFilename, comment);
        await sleep(100); // 0.2초 기다린 후 다시 시작
      }
    }
  }
};

processEntries()
  .then(() => console.log('Processing completed.'))
  .catch(error => console.error(`An error occurred: ${error.message}`));