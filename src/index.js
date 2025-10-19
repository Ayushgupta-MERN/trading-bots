// Entry point for the application

const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Welcome to the Automated Trading Bot!');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
