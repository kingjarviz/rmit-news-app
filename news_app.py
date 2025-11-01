# RMIT News & Events Advisor 

import streamlit as st
import json
import boto3
from datetime import datetime, timedelta
import rmit_scraper

# === Premium UI Design - MUST BE FIRST === #
st.set_page_config(
    page_title="RMIT News Hub",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# === AWS Configuration === #
COGNITO_REGION = "ap-southeast-2"
BEDROCK_REGION = "ap-southeast-2"
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
IDENTITY_POOL_ID = "ap-southeast-2:eaa059af-fd47-4692-941d-e314f2bd5a0e"
USER_POOL_ID = "ap-southeast-2_NfoZbDvjD"
APP_CLIENT_ID = "3p3lrenj17et3qfrnvu332dvka"
USERNAME = "s4181965@student.rmit.edu.au"
PASSWORD = "Annuanna@00"

# === AWS Functions === #
def get_credentials(username, password):
    idp_client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    response = idp_client.initiate_auth(
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
        ClientId=APP_CLIENT_ID,
    )
    id_token = response["AuthenticationResult"]["IdToken"]
    identity_client = boto3.client("cognito-identity", region_name=COGNITO_REGION)
    identity_response = identity_client.get_id(
        IdentityPoolId=IDENTITY_POOL_ID,
        Logins={f"cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}": id_token},
    )
    creds_response = identity_client.get_credentials_for_identity(
        IdentityId=identity_response["IdentityId"],
        Logins={f"cognito-idp.{COGNITO_REGION}.amazonaws.com/{USER_POOL_ID}": id_token},
    )
    return creds_response["Credentials"]

def build_news_prompt(articles, user_question, filters):
    """Build prompt with filtered articles"""
    if not articles:
        return f"""
I've searched through RMIT's latest news, but no articles match your current filters: {filters}

Please try:
- Selecting "All RMIT News" to see all available content
- Adjusting the time period filter
- Visiting the official RMIT website for complete information

User Question: "{user_question}"
"""
    
    # Format articles for the prompt
    articles_text = ""
    for i, article in enumerate(articles[:8], 1):
        days_ago = article.get('days_ago', 0)
        if days_ago == 0:
            recency = "🆕 TODAY"
        elif days_ago == 1:
            recency = "📅 YESTERDAY"
        else:
            recency = f"📅 {days_ago} DAYS AGO"
            
        source_indicator = "🌐 LIVE" if article.get('source') == 'live_rmit' else "📄 SAMPLE"
        
        articles_text += f"""
{i}. *{article.get('title', 'No title')}* {source_indicator}
   - ⏰ Published: {recency}
   - 📝 Summary: {article.get('summary', 'No summary available')}
   - 🔗 Link: {article.get('link', 'Not available')}
"""
    
    prompt = f"""
You are an RMIT University News Assistant. I've fetched relevant news based on the user's filters.

*CONTEXT:*
Active Filters: {filters}
Number of Relevant Articles: {len(articles)}
Data Source: RMIT University Website

*RELEVANT RMIT NEWS ARTICLES:*
{articles_text}

*USER QUESTION:*
"{user_question}"

*IMPORTANT INSTRUCTIONS:*
1. Use ONLY the provided articles to answer the question
2. Be specific - mention article titles and key details
3. Include relevant links when available
4. If the articles don't fully answer the question, acknowledge this honestly
5. Keep responses student-focused and helpful
6. Mention the recency of information when relevant

Provide a comprehensive, accurate response based on these articles.
"""
    return prompt

def invoke_bedrock(prompt_text, **kwargs):
    return "🤖 Demo mode active — AI response not available on Streamlit Cloud.\n\nHere's how your prompt would be processed:\n\n" + prompt_text[:600]

def apply_category_filter(articles, news_category):
    """Return articles filtered by selected category, or all if 'All News'."""
    if news_category == "All News":
        return articles
    cat = news_category.lower()
    return [a for a in articles if a.get("category", "All News").lower() == cat]

def filter_articles_by_time(articles, time_period):
    """Filter articles based on time period"""
    if time_period == "All Time":
        return articles
    
    current_date = datetime.now()
    filtered_articles = []
    
    for article in articles:
        days_ago = article.get('days_ago', 999)
        
        if time_period == "Last 7 Days" and days_ago <= 7:
            filtered_articles.append(article)
        elif time_period == "Last 30 Days" and days_ago <= 30:
            filtered_articles.append(article)
        elif time_period == "Last 3 Months" and days_ago <= 90:
            filtered_articles.append(article)
    
    return filtered_articles

# Modern CSS Design
st.markdown("""
<style>
    /* Modern Color Scheme */
    :root {
        --primary: #FF5A00;
        --primary-light: #FF8C00;
        --primary-dark: #CC4A00;
        --light: #F8FAFC;
        --dark: #1E293B;
        --gray: #64748B;
        --border: #E2E8F0;
        --success: #10B981;
    }
    
    /* Global Styles */
    .main {
        background: #f8fafc;
    }
    
    .main .block-container {
        padding-top: 1rem;
        max-width: 100%;
    }
    
    /* Header */
    .header-container {
        background: white;
        padding: 2rem 0 1rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid var(--border);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin: 0;
    }
    
    .sub-title {
        font-size: 1.1rem;
        color: var(--gray);
        text-align: center;
        margin: 0.5rem 0 0 0;
    }
    
    /* Cards */
    .glass-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--border);
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .metric-card {
        background: linear-gradient(135deg, var(--primary), var(--primary-light));
        color: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
    }
    
    .article-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border: 1px solid var(--border);
        border-left: 4px solid var(--primary);
    }
    
    /* Inputs */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 8px;
        border: 1px solid var(--border);
        padding: 0.75rem;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: var(--primary);
        box-shadow: 0 0 0 2px rgba(255, 90, 0, 0.1);
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        border: none;
        padding: 0.75rem 1.5rem;
        background: var(--primary);
        color: white;
    }
    
    .stButton>button:hover {
        background: var(--primary-dark);
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--dark);
        margin: 1.5rem 0 1rem 0;
    }
    
    .category-tag {
        background: rgba(255, 90, 0, 0.1);
        color: var(--primary);
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .time-badge {
        background: var(--success);
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown(
    """
    <div class="header-container" 
         style="background: white; padding: 1.5rem 0; margin-bottom: 1rem;
                border-bottom: 1px solid #E2E8F0; display: flex; flex-direction: column; 
                align-items: center; text-align: center;">
        <!-- Inline logo + title -->
        <div style="display: flex; align-items: center; justify-content: center; gap: 0rem;">
            <img src="https://mams.rmit.edu.au/ywta8fdr0jdhz.jpg"
                 alt="RMIT University Logo"
                 style="height: 100px;">
            <h1 style="color: black; font-weight: 800; font-size: 3.5rem; margin: 0;">
                NEWS HUB
            </h1>
        </div>
        <!-- Centered subtitle -->
        <p style="font-size: 1.1rem; color: #64748B; margin: 0.5rem 0 0; text-align: center;">
            Stay informed with the latest university news and updates
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Initialize session state for articles
if 'articles' not in st.session_state:
    st.session_state.articles = []

# Main Layout - Clean 3-column structure
col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    # Sidebar - Filters
    st.markdown("### 🎯 Filters")
    
    st.markdown("*Category*")
    news_category = st.radio(
        "Select news type:",
        ["All News", "Technology", "Science"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("*Time Period*")
    time_period = st.radio(
        "Select time range:",
        ["All Time", "Last 7 Days", "Last 30 Days", "Last 3 Months"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    # Load news data once and cache it
    if not st.session_state.articles:
    with st.spinner("🔄 Loading cached sample news..."):
        st.session_state.articles = rmit_scraper.load_news_cache() or [
            {
                "title": "RMIT launches AI innovation hub",
                "link": "https://www.rmit.edu.au/news",
                "summary": "RMIT University unveils its new AI and technology initiative.",
                "published": "Fri, 31 Oct 2025 13:21:50 GMT",
                "days_ago": 0,
                "category": "Technology",
                "source": "demo_cache"
            }
        ]
    
    articles = st.session_state.articles
    
    if articles:
        # Apply time filter for stats
        time_filtered_articles = filter_articles_by_time(articles, time_period)
        
        st.metric("Total Articles", len(time_filtered_articles))
        
        # Category counts with time filter
        counts = {
            "All News": len(time_filtered_articles),
            "Technology": sum(1 for a in time_filtered_articles if a.get('category', '').lower() == 'technology'),
            "Science": sum(1 for a in time_filtered_articles if a.get('category', '').lower() == 'science')
        }


        # Display metrics in 2-column layout
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Technology", counts["Technology"])
            st.metric("Science", counts["Science"])

        # Time period info
        st.markdown("---")
        st.markdown("### ⏰ Time Filter")
        st.info(f"Showing: *{time_period}*\n\n**{len(time_filtered_articles)}** articles match your filters")
        
    else:
        st.info("No articles loaded")

with col2:
    # --- Dynamic, category-specific quick questions ---
    CATEGORY_QUESTIONS = {
        "All News": [
            "What's happening at RMIT this week?",
            "Show me the latest university announcements",
            "Any major achievements or awards recently?",
            "What are the big stories across the uni right now?"
        ],
        "Technology": [
            "What's new in RMIT's technology research?",
            "Latest computing and AI developments",
            "Cybersecurity initiatives and projects",
            "Tech industry partnerships at RMIT"
        ],
        "Science": [
            "Recent scientific breakthroughs at RMIT",
            "New publications from RMIT researchers",
            "What labs or studies were featured lately?",
            "Any environment or climate-related findings?"
        ]
    }

    # Pull relevant list for the selected category, fall back to “All News”
    example_questions = CATEGORY_QUESTIONS.get(news_category, CATEGORY_QUESTIONS["All News"])

    # --- Quick questions (robust, no callback needed) ---

# Make sure a place exists to store the typed question
    if "user_question" not in st.session_state:
        st.session_state.user_question = ""

    st.markdown("Pick a question from the dropdown box below (Select 'Type your own' for custom queries):")

    # Build options for the current category
    example_questions = CATEGORY_QUESTIONS.get(
        news_category,
        CATEGORY_QUESTIONS["All News"]
    )
    quick_options = ["Type your own"] + example_questions

    # Show the dropdown (keep label visible so it can't 'disappear')
    selected_question = st.selectbox(
        "Quick Questions",
        quick_options,
        index=0,
        key=f"qpick_{news_category}"  # unique per category prevents key collisions
    )

    # Prefill the text area when a question is picked
    if selected_question != "Type your own":
        st.session_state.user_question = selected_question

    # The input users will actually submit
    user_question = st.text_area(
        "Your question:",
        key="user_question",
        placeholder="Ask about RMIT news, events, research, or campus updates...",
        height=100
    )


    
    # Generate button
    if st.button("🚀 Get Intelligent Analysis", use_container_width=True, type="primary"):
        if not user_question.strip():
            st.warning("Please enter a question")
        else:
            try:
                with st.spinner("🔍 Analyzing relevant news..."):

                    filtered_articles = apply_category_filter(articles.copy(), news_category)
                    filtered_articles = filter_articles_by_time(filtered_articles, time_period)

                    # Build filters description
                    filters_desc = f"Category: {news_category}, Time: {time_period}"
                    
                    # Show filtering results
                    if filtered_articles:
                        st.success(f"✅ Found {len(filtered_articles)} relevant articles!")
                    else:
                        st.warning(f"⚠️ No articles found for your filters. Showing all articles.")
                        filtered_articles = articles
                    
                    # Get AI response
                    prompt = build_news_prompt(filtered_articles, user_question, filters_desc)
                    answer = invoke_bedrock(prompt)
                    
                    # Display results
                    st.markdown("---")
                    st.markdown("### 🤖 News Analysis")
                    st.write(answer)
                    
                    # Show articles used
                    if filtered_articles:
                        st.markdown("---")
                        st.markdown(f"### 📋 Reference Articles ({len(filtered_articles)} found)")
                        
                        for i, article in enumerate(filtered_articles[:6], 1):
                            source_badge = "🌐 LIVE" if article.get('source') == 'live_rmit' else "📄 SAMPLE"
                            days_ago = article.get('days_ago', 0)
                            time_badge = "🆕 TODAY" if days_ago == 0 else f"📅 {days_ago}D"
                            
                            with st.expander(f"{i}. {article.get('title', 'No title')} {source_badge} {time_badge}", expanded=False):
                                st.write(f"*Published:* {article.get('published', 'Unknown')} ({days_ago} days ago)")
                                st.write(f"*Summary:* {article.get('summary', 'No summary available')}")
                                if article.get('link') and article.get('link') != '#':
                                    st.write(f"🔗 [Read full article]({article.get('link')})")

            except Exception as e:
                st.error(f"Error processing your request: {str(e)}")

with col3:
    # Right Column - Latest News Preview
    st.markdown("### 📰 Latest News")
    
    if articles:

        preview_articles = apply_category_filter(articles.copy(), news_category)
        preview_articles = filter_articles_by_time(preview_articles, time_period)

        # Show up to 3 articles in preview
        for i, article in enumerate(preview_articles[:3]):
            category = article.get('category', 'General')
            source_badge = "🌐" if article.get('source') == 'live_rmit' else "📄"
            days_ago = article.get('days_ago', 0)
            time_indicator = "🆕" if days_ago == 0 else f"{days_ago}d"
            
            st.markdown(f"""
            <div class="article-card">
                <div style="margin-bottom: 0.5rem;">
                    <strong>{article.get('title', 'No title')}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <span class="category-tag">{category}</span>
                    <div>
                        <small style="color: var(--gray); margin-right: 0.5rem;">{source_badge}</small>
                        <small style="color: var(--success); font-weight: 600;">{time_indicator}</small>
                    </div>
                </div>
                <p style="font-size: 0.8rem; color: var(--gray); margin: 0;">
                    {article.get('summary', 'No summary')[:80]}...
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        if not preview_articles:
            st.info("No articles match your current filters")
    else:
        st.info("Loading news articles...")

# Bottom Section - More Headlines (FIXED)
st.markdown("---")
st.markdown("### 🗞️ More Headlines")

if articles:
    # Apply both category and time filters for more headlines
    more_articles = apply_category_filter(articles.copy(), news_category)
    more_articles = filter_articles_by_time(more_articles, time_period)

    
    # Skip the first 3 articles (already shown in preview) and take next 6
    if len(more_articles) > 3:
        additional_articles = more_articles[3:9]
        
        if additional_articles:
            # Create columns for the grid
            cols = st.columns(3)
            for i, article in enumerate(additional_articles):
                with cols[i % 3]:
                    category = article.get('category', 'General')
                    source_badge = "🌐" if article.get('source') == 'live_rmit' else "📄"
                    days_ago = article.get('days_ago', 0)
                    time_indicator = "TODAY" if days_ago == 0 else f"{days_ago} days ago"
                    
                    st.markdown(f"""
                    <div style="padding: 1rem; border: 1px solid var(--border); border-radius: 8px; height: 160px; margin-bottom: 1rem; background: white;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                            <span class="category-tag">{category}</span>
                            <small style="color: var(--gray);">{source_badge}</small>
                        </div>
                        <strong style="font-size: 0.9rem; display: block; margin-bottom: 0.5rem;">{article.get('title', 'No title')}</strong>
                        <p style="font-size: 0.8rem; color: var(--gray); margin: 0.5rem 0 0 0; line-height: 1.3;">
                            {article.get('summary', 'No summary available')[:90]}...
                        </p>
                        <div style="margin-top: 0.5rem;">
                            <small style="color: var(--success); font-weight: 600;">{time_indicator}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No more articles to show")
    else:
        st.info("No additional articles beyond the preview")
else:
    st.info("Loading news articles...")

# Refresh button in footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🔄 Refresh News Data", use_container_width=True):
        import os
        if os.path.exists('news_cache.json'):
            os.remove('news_cache.json')
        st.session_state.articles = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: var(--gray); font-size: 0.9rem; padding: 1rem 0;'>"
    "🎓 <strong>RMIT University</strong> • Melbourne, Australia • Live News Updates"
    "</div>",
    unsafe_allow_html=True
)
