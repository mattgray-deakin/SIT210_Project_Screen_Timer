/*
SIT210 - Embedded Systems Development
Screen Time Monitor Project
Matthew Gray

This Arduino/Particle Firmware is Developed for the Particle Argon
In this script, the Argon communicates with a Raspberry Pi (Attachment via Serial Required)

The purpose of the firmware is to recieve data about various monitored device and provide an output via and LCD Display.

The device will also communicate with the Particle Cloud, which allows integration with IFTTT.

It is used to monitor device usage for digital health of children
*/
#include "LiquidCrystal_I2C_Spark.h"

LiquidCrystal_I2C *lcd;

// Setup char array for serial interface
const byte char_max = 40;
char ser_rcv[char_max];
// Setup datarcv flag that identifies if new data has been recieved via serial
boolean datarcv = false;
// Publish counter - Once this reaches 20, read_device_data procedure will send a device update to Particle Cloud
int publish_counter = 0;

// Setup Serial1 (Not the USB Connection! This is using RX(D10),TX(D9) and GND for UART) and the I2C LCD Display
void setup(void)
{
  Serial1.begin(9600);
  lcd = new LiquidCrystal_I2C(0x27, 20, 4);
  lcd->init();
  lcd->backlight();
  lcd->clear();
  lcd->print("Screen Timer Init");
}

// Procedure to Recieve Data via the Serial Interface using the [data] protocol
void ser_recieve()
{
  static boolean receiving_data = false;                                    // Flag to id if data receipt is currently in progress
  static byte index = 0;                                                    // Start with an index of 0 for the array
  char data_starter = '[';                                                  // Start Character for data
  char data_ender = ']';                                                    // End Character for data
  char rx_char;                                                             // Storage for the currently recieved character

  while (Serial1.available() > 0 && datarcv == false)                       // Check if there is Serial data, and we have not just finished recieving data (Ignores data after a ']')
  {
    rx_char = Serial1.read();                                               // Read the char in

    if (receiving_data == true)                                             // If currently recieving data then
    {

      if (rx_char != data_ender)                                            // Check if the character was the end of a string of data, if it isn't add it to the string and increment index
      {
        ser_rcv[index] = rx_char;
        index++;

        if (index >= char_max)                                     // If we have hit maximum character limit, ignore
        {
          index = char_max - 1;
        }
      }

      else                                                         // If it is the data ender - End of the string.  Stop receiving data reset the index and set the new serial data flag to true.
      {
        ser_rcv[index] = '\0';
        receiving_data = false;
        index = 0;
        datarcv = true;
      }
    }

    else if (rx_char == data_starter)                               // If data not yet being recieved, check if this is that start character.  If it is, start recieving the data.
    {
      receiving_data = true;
    }
  }
  
}
// This procedure Reads data from the Serial Interface and sends it on to the Display Data Procedure.
void read_device_data(){
  // Initial setup procedures
  int index, time;
  String name, pub_str;
  bool index_ck, name_ck, time_ck;
  index = -1;
  time = -1;
  name = "";
  delay(2000);      // Random short delay to load up Serial Data in the buffer
  index_ck = name_ck = time_ck = 0;

  if (time_ck == 0 ){                                 // Confirm if a remaining time for this device has been recieved ... if not we can start these loops
    while (index_ck == 0){                            // Index for the device check, loop until it is received
      ser_recieve();                                  // Recieve serial data
      if (datarcv == true){                           // Confirm there is serial data, if not .. wait
        index = atoi(ser_rcv);                        // change the serial string to an integer
        datarcv = false;                              // Data is used, flip the flag for new serial data back
        ser_rcv[0] = '\0';                            // Clear the serial recieve string once applied
        if (index != -1) {                            // If there is a new value in index, change the flag to exit the loop
          index_ck = 1;
        }
       }
    }

    while (name_ck == 0){                             // Do we have a device name yet, if not start the loop and get one
      ser_recieve();                                  // Recieve the serial data
      if (datarcv == true){                             
        name = ser_rcv;                               // Load data into the name string
        datarcv = false;
        ser_rcv[0] = '\0';
        if (name != ""){
          name_ck = 1;
        }
      }
    }

    while (time_ck == 0){                             // As previous, but with time remaining
      ser_recieve();
      if (datarcv == true){
        time = atoi(ser_rcv);
        datarcv = false;
        ser_rcv[0] = '\0';
        if (time != -1){
          time_ck = 1;
        }
      }
    }
    if (index < 4){                                   // Only four lines on LCD, therefore can only show 4 devices at once
      display_data(index, name, time);                // Send data to the LCD using display dat procedure
    }
    publish_counter++;                                // Update the publish counter

    if (publish_counter == 20){                       // If the counter is at 20, send a message to Particle Cloud, and reset the timer
      Particle.publish("Dev in Use", name);
      publish_counter = 0;
    }
  }
}
// Procedure to send an Alarm to the Particle Cloud and the LCD Display
void send_alarm(){
  String dev_at_limit;
  lcd->clear();
  lcd->print("Device Overtime");
  ser_recieve();
  dev_at_limit = ser_rcv;
  lcd->setCursor(0, 2);
  lcd->print(dev_at_limit);
  Particle.publish("Limit Reached", dev_at_limit);    // Published in a format that IFTTT is configured to understand.  IFTTT will show #Device# is over limit
  ser_rcv[0] = '\0';                                  // Clear the Serial String and set the new data flag to false
  datarcv = false;

}

// Procedure to clear the LCD
void clear_display(){
  lcd->clear();
  lcd->setCursor(3, 0);
  lcd->print("Awaiting Data");
  lcd->setCursor(3, 2);
  lcd->print("Or no Devices");
}

// Main Serial selection/Menu style list for the main loop
void serial_selector(){
  // Recieve the Data, run through the if statement and select the desired outcome
  ser_recieve();
  if (datarcv == true){
    if (atoi (ser_rcv) == 1){                       // 1 - New Device Data, run to the read_device_data procedure to update the LCD
      ser_rcv[0] = '\0';
      datarcv = false;
      read_device_data();

    }
    else if (atoi (ser_rcv) == 2){                  // 2 - A device is overtime, send the alarm to LCD and Particle Cloud
      ser_rcv[0] = '\0';
      datarcv = false;
      send_alarm();
    }
    else if (atoi (ser_rcv) == 3){                  // 3 - Clear the display as there are no devices being monitored anymore
      ser_rcv[0] = '\0';
      clear_display();
      datarcv = false;
    }
    else if (atoi (ser_rcv) == 4){                  // 4 - Clear the display, as a change in data warrants a change in display information
      ser_rcv[0] = '\0';
      lcd->clear();
      datarcv = false;
    }
    else {
      Serial1.println("Error in Serial Selection"); // If there is an incorrect input, and error is sent to the serial interface
      ser_rcv[0]='\0';
      datarcv = false;
    }
  }
}
/*
Display Device Data to the LCD Display
index - index of the device - used to position on the display (0 will display at top, 1 on second line, etc)
name - the name of the device
time - time remaining in seconds
*/
void display_data(int index, String name, int time){
  lcd->setCursor(0, index);
  lcd->print((time / 60));            // Time converted into minutes
  lcd->print(" min ");
  lcd->print(name);
}

// Main loop, only needs to run serial_selectore
void loop(void)
{
  serial_selector();
}