"""
SQL Queries for Wired Articles Reporting
"""
import psycopg2


DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "wired_db",
    "user": "postgres",
    "password": "postgres"
}


def get_connection():
    return psycopg2.connect(**DB_PARAMS)


def query_1_clean_author_names():
    """
    Query 1: Tampilkan judul artikel dan nama author yang sudah dibersihkan dari kata "By" di depannya.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            title,
            CASE 
                WHEN author LIKE 'By%' THEN SUBSTRING(author FROM 3 FOR CHAR_LENGTH(author) - 2)
                ELSE author
            END AS clean_author
        FROM wired_articles
        WHERE author IS NOT NULL AND author != ''
        ORDER BY id;
    """)
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return results


def query_2_top_authors():
    """
    Query 2: Tampilkan 3 nama penulis yang paling sering muncul dalam database hasil scrape kalian.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            CASE 
                WHEN author LIKE 'By%' THEN SUBSTRING(author FROM 3 FOR CHAR_LENGTH(author) - 2)
                ELSE author
            END AS author_name,
            COUNT(*) AS article_count
        FROM wired_articles
        WHERE author IS NOT NULL AND author != ''
        GROUP BY author
        ORDER BY article_count DESC
        LIMIT 3;
    """)
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return results


def query_3_search_keywords():
    """
    Query 3: Cari artikel yang mengandung kata kunci "AI", "Climate", atau "Security" 
    pada judul atau deskripsi.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT title, description, author
        FROM wired_articles
        WHERE 
            title ILIKE '%AI%'
            OR title ILIKE '%Climate%'
            OR title ILIKE '%Security%'
            OR description ILIKE '%AI%'
            OR description ILIKE '%Climate%'
            OR description ILIKE '%Security%'
        ORDER BY id;
    """)
    
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return results


def run_all_queries():
    """Execute all queries and display results."""
    print("=" * 80)
    print("QUERY 1: Judul artikel dan nama author (tanpa 'By')")
    print("=" * 80)
    results = query_1_clean_author_names()
    for row in results:
        print(f"Title: {row[0][:60]}...")
        print(f"Author: {row[1]}")
        print("-" * 40)
    
    print("\n" + "=" * 80)
    print("QUERY 2: 3 Penulis paling sering muncul")
    print("=" * 80)
    results = query_2_top_authors()
    for row in results:
        print(f"Author: {row[0]} | Jumlah Artikel: {row[1]}")
    
    print("\n" + "=" * 80)
    print("QUERY 3: Artikel dengan keyword AI, Climate, atau Security")
    print("=" * 80)
    results = query_3_search_keywords()
    for row in results:
        print(f"Title: {row[0][:60]}...")
        print(f"Description: {row[1][:80] if row[1] else 'N/A'}...")
        print(f"Author: {row[2]}")
        print("-" * 40)
    
    if not results:
        print("Tidak ada artikel yang cocok dengan keyword tersebut.")


if __name__ == "__main__":
    run_all_queries()