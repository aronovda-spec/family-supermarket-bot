# Voice Search Deployment Guide

## Overview
This guide explains how to deploy the shopping bot with voice search functionality on Render and other cloud platforms.

## Dependencies Added
The following dependencies have been added to `requirements.txt`:
- `pydub==0.25.1` - Audio processing library
- `ffmpeg-python==0.2.0` - FFmpeg wrapper for audio conversion

## Render Deployment

### 1. Build Command
Add the following build command to your Render service:

```bash
pip install -r requirements.txt
```

### 2. Environment Variables
No additional environment variables are required for basic voice search functionality.

### 3. FFmpeg Installation
For Render deployment, you may need to install FFmpeg. Add this to your build command:

```bash
# Install system dependencies
apt-get update && apt-get install -y ffmpeg

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Alternative: Use Render's FFmpeg Buildpack
If the above doesn't work, you can use a custom buildpack:

1. Go to your Render service settings
2. Add a buildpack: `https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git`
3. Then use the standard build command: `pip install -r requirements.txt`

## Voice Search Features

### What Works
- ✅ Voice message reception
- ✅ Audio format conversion (OGG to WAV)
- ✅ Multiple recognition methods (Google, Sphinx)
- ✅ Fallback to manual text input
- ✅ Cross-platform compatibility

### Limitations on Cloud Platforms
- ⚠️ Google Speech Recognition requires internet connection
- ⚠️ Sphinx (offline) recognition may have limited accuracy
- ⚠️ Audio processing may be slower on shared hosting

### Fallback Behavior
When voice recognition fails, the bot will:
1. Show helpful error messages
2. Provide manual text input option
3. Give tips for better voice recognition
4. Continue with normal search functionality

## Testing Voice Search

### Local Testing
1. Run the bot locally
2. Send a voice message
3. Check logs for recognition results

### Production Testing
1. Deploy to Render
2. Test voice search functionality
3. Monitor logs for any issues
4. Verify fallback behavior works

## Troubleshooting

### Common Issues

#### 1. "Speech recognition library not installed"
- Check that `SpeechRecognition==3.10.0` is in requirements.txt
- Verify the package is installed during build

#### 2. "Audio conversion failed"
- Ensure `pydub` is installed
- Check if FFmpeg is available on the system
- Verify audio file format compatibility

#### 3. "Voice recognition failed"
- This is normal - the bot will fall back to manual input
- Check internet connection for Google recognition
- Try speaking more clearly or reducing background noise

#### 4. "No working recognition methods found"
- Check system dependencies
- Verify internet connectivity
- Consider using offline recognition methods

### Debug Information
The bot now provides detailed status information:
- Available recognition methods
- System limitations
- Helpful error messages
- Fallback options

## Performance Considerations

### Audio Processing
- Voice files are converted to WAV format for better compatibility
- Processing time depends on audio length and server performance
- Temporary files are automatically cleaned up

### Memory Usage
- Audio processing uses temporary memory
- Files are processed in chunks to minimize memory usage
- Automatic cleanup prevents memory leaks

### Network Usage
- Google recognition requires internet connection
- Audio files are downloaded and processed locally
- No audio data is sent to external services (except Google for recognition)

## Security Notes

### Data Privacy
- Voice files are processed locally
- Only transcribed text is used for search
- No voice data is stored permanently
- Temporary files are automatically deleted

### API Keys
- Google Speech Recognition uses free API (no key required)
- No additional authentication needed
- Rate limits apply to Google's free service

## Monitoring

### Log Messages
The bot logs important events:
- Voice file download status
- Audio conversion results
- Recognition method attempts
- Success/failure status
- Error details for debugging

### Health Checks
- Voice search availability is checked on startup
- Status is displayed to users
- Fallback options are always available

## Future Improvements

### Potential Enhancements
1. **Offline Recognition**: Improve Sphinx accuracy
2. **Multiple Languages**: Add more language support
3. **Audio Quality**: Implement noise reduction
4. **Caching**: Cache recognition results
5. **Analytics**: Track recognition success rates

### Platform-Specific Optimizations
1. **Render**: Optimize for serverless environment
2. **Heroku**: Use buildpacks for audio processing
3. **AWS**: Leverage AWS Transcribe service
4. **Google Cloud**: Use Google Speech-to-Text API

## Support

### Getting Help
1. Check the logs for error messages
2. Test voice search functionality
3. Verify all dependencies are installed
4. Check system requirements

### Reporting Issues
When reporting voice search issues, include:
- Platform (Render, local, etc.)
- Error messages from logs
- Voice message characteristics (length, quality)
- Expected vs actual behavior
