const express = require('express');
const { Pool } = require('pg');
const path = require('path');

const app = express();
const port = process.env.PORT || 8081; // Railway dynamic port

// PostgreSQL connection using DATABASE_URL
const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

app.use(express.static('public'));

// Serve main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// API endpoint for vote results
app.get('/api/results', async (req, res) => {
    try {
        const result = await pool.query(`
            SELECT vote, COUNT(*) as count 
            FROM votes 
            GROUP BY vote
        `);
        
        const results = { a: 0, b: 0 };
        result.rows.forEach(row => { results[row.vote] = parseInt(row.count); });
        
        res.json(results);
    } catch (err) {
        console.error('Error querying database:', err);
        res.json({ a: 0, b: 0 });
    }
});

app.listen(port, '0.0.0.0', () => {
    console.log(`Results app listening on port ${port}`);
});
