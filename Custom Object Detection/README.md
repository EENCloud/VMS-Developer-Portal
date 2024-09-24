# Eagle Eye Networks Custom Object Detection Example

This sample Flask application connects to an Eagle Eye Networks account and runs an object detection model against one of the live RTSP feeds.  To run this application, you will need to have a valid Eagle Eye Networks account and an application registered with the Eagle Eye Networks Developer Program. For more information on how to register an application, review the [API documentation](https://developer.eagleeyenetworks.com/docs/getting-started).

The script uses the [Ultralytics YOLO](https://docs.ultralytics.com/) object detection model to detect objects in the live video feed. The bounding boxes for the objects are then displayed on the video feed in real time.


## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Clone this repository or copy the sample code into your local environment.

3. Create a copy of `example.flaskenv` and rename it `.flaskenv`. Update the `CLIENT_ID` and `CLIENT_SECRET` in the file with your application's credentials. For more details on obtaining these credentials, visit our [API documentation](https://developer.eagleeyenetworks.com/docs/client-credentials).

4. Update the FLASK_APP environment variable:
   ```
   $ export FLASK_APP=detect.py
   ```


## Running the Application

To start the server:
```
python -m flask run
```
This will host a local server on `127.0.0.1:3333`.

## Usage

1. Navigate to `http://127.0.0.1:3333` in your web browser.
2. Click on the "Login with Eagle Eye Networks" link to authenticate.
3. Once you log in, you will be redirected to the camera select page.
4. Select a camera view to start the object detection.


## About Yolo

Yolo (You Only Look Once) is a state-of-the-art, real-time object detection system that has significantly advanced the field of computer vision. Introduced by Joseph Redmon and Ali Farhadi, Yolo's unique approach to object detection allows for simultaneous object classification and localization, making it one of the fastest and most efficient models available.

Yolo v8 builds on the success of its predecessors by incorporating advancements in architecture, training techniques, and optimization strategies. These improvements enhance its accuracy and speed, making it suitable for a wide range of applications, from surveillance systems to autonomous vehicles and beyond. Yolo v8 excels in scenarios where real-time processing is crucial, delivering high performance without compromising on precision.

### Supported Classes

Yolo v8 is typically trained on the COCO (Common Objects in Context) dataset, which includes 80 different object classes. These classes range from everyday objects to various animals and vehicles, allowing for versatile detection capabilities. The full list of COCO classes includes:

1. **Person**: person
2. **Vehicle**: bicycle, car, motorcycle, airplane, bus, train, truck, boat
3. **Outdoor**: traffic light, fire hydrant, stop sign, parking meter, bench
4. **Animal**: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe
5. **Accessory**: backpack, umbrella, handbag, tie, suitcase
6. **Sports**: frisbee, skis, snowboard, sports ball, kite, baseball bat, baseball glove, skateboard, surfboard, tennis racket
7. **Kitchen**: bottle, wine glass, cup, fork, knife, spoon, bowl
8. **Food**: banana, apple, sandwich, orange, broccoli, carrot, hot dog, pizza, donut, cake
9. **Furniture**: chair, couch, potted plant, bed, dining table, toilet
10. **Electronic**: TV, laptop, mouse, remote, keyboard, cell phone
11. **Appliance**: microwave, oven, toaster, sink, refrigerator
12. **Indoor**: book, clock, vase, scissors, teddy bear, hair drier, toothbrush

### Training the Model

While Yolo v8 comes pre-trained on the COCO dataset, you may need to detect objects not included in COCO or improve accuracy for specific objects in your context. In such cases, you can fine-tune or retrain Yolo v8 on a custom dataset. This involves collecting and annotating images with your objects of interest, converting the dataset to the required format, and training the model using the Yolo training script.

For detailed instructions on training Yolo v8 on a custom dataset, refer to the [Yolo v8 documentation](https://docs.ultralytics.com).

### Bandwidth Usage

The bandwidth required for Yolo v8 to analyze a live video stream depends on several factors, including the resolution, frame rate, and compression method used. For a rough estimate:

- **720p at 30 fps**: ~1-3 Mbps
- **1080p at 30 fps**: ~3-6 Mbps
- **4K at 30 fps**: ~15-30 Mbps

In our demonstration, we're utilizing the preview stream of Eagle Eye Networks VMS, which typically has a resolution of 640p and a frame rate of 1 fps. We've chosen this route because of the ease of implementation and the ability to demonstrate the Yolo v8 model in real time. The preview stream, while lower in resolution and frame rate, still provides a good representation of the model's capabilities.

For tasks requiring higher resolution or extremely low latency, such as weapons or threat detection, it's recommended to use the full video stream. In these cases, you may consider creating an appliance that can process the video stream locally. This will greatly reduce the bandwidth usage and provide better performance.

### Recommended Resolutions

Yolo v8 can operate at various resolutions, balancing detection accuracy and computational efficiency. Common resolutions used in practice include:

- **416x416**: Suitable for real-time applications with faster processing times.
- **608x608**: A middle ground offering a balance between speed and accuracy.
- **1280x1280**: Provides higher accuracy but requires more computational resources and may be slower for real-time processing.

Choosing the right resolution depends on the application requirements and the available computational power.

## Handling the Detection Results

Once Yolo v8 processes the live stream, it generates detections for each frame. These detections need to be handled appropriately to visualize the results and extract meaningful information. Below is a detailed explanation of how to handle the detection results, including code snippets for better understanding.

### Loading the YOLO Model and Generating Detections

First, we load the Yolo model and generate detections from the live stream. The model returns a generator that allows us to iterate over each frame and its detection results.

```python
# Load the YOLO model and generate detections.
# The model will return a generator that allows us to
# iterate over each frame and its detection results.
model = YOLO('yolov8s.pt')
results = model(source=auth_url, show=False, conf=0.40, stream=True)
```

### Iterating Over Detection Results

Next, we iterate over the detection results. For each frame, we check if any objects are detected. If objects are detected, we draw bounding boxes and labels on the frame to visualize the detections.

```python
for i in results:
 frame = i.orig_img
    print(f"Original Frame Shape: {i.orig_shape}")
    if len(i.boxes.cls) > 0:
        # For each detected object, draw the bounding boxes
        # and labels on the frame
        for n, detection in enumerate(i.boxes.cls):
 coord = [
                int(i.boxes.xyxy[n][0]),
                int(i.boxes.xyxy[n][1]),
                int(i.boxes.xyxy[n][2]),
                int(i.boxes.xyxy[n][3])
 ]
 label = i.names[int(detection)]
 cv2.rectangle(
 frame,
 ((coord[0]), coord[1]),
 (coord[2], coord[3]),
 (218, 145, 0),
                2)
 cv2.putText(
 frame,
                f"{label} {i.boxes.conf[n]:.2f}",
 (coord[0], coord[1] - 10),
 cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
 (172, 103, 0),
                2)
```

In this code:
- We retrieve the original frame from the detection result.
- We print the original frame shape for reference.
- If any objects are detected (i.e., the `boxes.cls` list is not empty), we iterate over each detected object.
- For each detected object, we extract the coordinates of the bounding box and the label.
- We draw a rectangle around the detected object using `cv2.rectangle`.
- We add a label above the bounding box using `cv2.putText`, which includes the object name and the confidence score.

### Encoding the Frame and Yielding the Result

After processing each frame, we encode it as a JPEG image and yield it as a byte stream. This step is crucial for streaming the processed video to a client or web application.

```python
ret, buffer = cv2.imencode('.jpg', frame)
frame = buffer.tobytes()
yield (b'--frame\r\n'
       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
```

In this code:
- We use `cv2.imencode` to encode the frame as a JPEG image.
- We convert the encoded image to bytes.
- We yield the byte stream in a format suitable for HTTP streaming, including the appropriate headers.

By following these steps, we can effectively handle the detection results from Yolo v8 and visualize the detected objects on the live video stream.

### Other Options for Handling Results

In addition to visualizing detections on the video stream, there are other powerful ways to handle detection results, especially when integrated with the Eagle Eye Networks Video Management System (VMS):

**Creating an EEN Event**
The Eagle Eye Networks VMS allows you to create custom events based on object detection results. By sending a POST request to [/events](https://developer.eagleeyenetworks.com/reference/createevent), you can create an event with the relevant information, such as the object detected, the confidence score, and the timestamp. This can also trigger further actions within the VMS, such as sending notifications or activating alarms.

**Triggering an EEN Alert**
EEN Events can trigger Alerts as part of the Alert Manager system. These alerts can be configured to notify end users when specific objects are detected. This could include sending push notifications, emails, or SMS alerts. By leveraging the VMS's alerting capabilities, you can ensure that users are immediately informed of important detections.

**Triggering a Real-Time Response**
In addition to alerting a user, Alerts can also be used to trigger actions in real-time through our partner integrations. For example, if a detected object poses a threat, the system can automatically trigger responses such as locking down a room, sounding alarms, or notifying security personnel. This can be achieved by linking the detection results with the access control API to automate responses.

By exploring these options, you can significantly enhance the functionality and effectiveness of your object detection system, providing real-time responses and improving overall security and operational efficiency.

## Support

If you encounter any issues or require further assistance, please contact our support team or refer to our comprehensive API documentation.