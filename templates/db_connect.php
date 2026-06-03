<?php
/*
* Yeh file database se connection banati hai.
* Ismein database ke credentials (server, username, password, database name) hain.
*/

// Database credentials
$servername = "localhost"; // Hamara server localhost hai
$username = "root";      // XAMPP ka default username 'root' hota hai
$password = "";          // XAMPP ka default password khali hota hai
$dbname = "goskillnexa_db"; // Hamare database ka naam

// Connection banane ki koshish karein
$conn = new mysqli($servername, $username, $password, $dbname);

// Connection check karein
if ($conn->connect_error) {
  // Agar connection fail ho jaye, toh error dikhakar script band kar dein
  die("Connection failed: " . $conn->connect_error);
}
?>