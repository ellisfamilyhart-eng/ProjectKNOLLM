#!/usr/bin/env python3
"""
Jarvix NoLLM v2.0 Flask Web Server
REST API with imagination, conversation, web learning, and Q&A
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from collections import defaultdict

# Import modular Jarvix v2.0
from jarvix import Jarvix, InputParser, ResponseGenerator
from jarvix.config import STORAGE_CONFIG

# Override data file
STORAGE_CONFIG['data_file'] = '/app/data/jarvix_v2_memory.json'

def create_app():
    app = Flask(__name__, template_folder='/app/templates')
    CORS(app)

    agent = None

    def get_agent():
        nonlocal agent
        if agent is None:
            agent = Jarvix(data_file=STORAGE_CONFIG['data_file'])
        return agent

    @app.route('/')
    def index():
        return render_template('index.html')

    # ========== CORE CHAT & LEARNING ==========

    @app.route('/api/chat', methods=['POST'])
    def chat():
        """Process user message"""
        data = request.json
        user_input = data.get('message', '').strip()
        
        if not user_input:
            return jsonify({'error': 'Empty message'}), 400
        
        try:
            agent = get_agent()
            response = agent.process_input(user_input)
            
            return jsonify({
                'success': True,
                'response': response,
                'mood': agent.brain.emotional_state,
                'total_interactions': agent.memory.total_interactions,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/stats', methods=['GET'])
    def stats():
        """Get agent statistics"""
        try:
            agent = get_agent()
            return jsonify({
                'success': True,
                'stats': agent.get_stats(),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/memory', methods=['GET'])
    def memory():
        """Get agent memory"""
        try:
            agent = get_agent()
            
            memory_data = {}
            for topic, facts in agent.memory.facts.items():
                sorted_facts = sorted(facts.items(), key=lambda x: -x[1])[:5]
                memory_data[topic] = [
                    {'fact': fact, 'confidence': round(conf, 2)} 
                    for fact, conf in sorted_facts
                ]
            
            return jsonify({
                'success': True,
                'memory': memory_data,
                'total_topics': len(agent.memory.facts),
                'total_facts': sum(len(f) for f in agent.memory.facts.values()),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/forget', methods=['POST'])
    def forget():
        """Clear all memories"""
        try:
            agent = get_agent()
            agent.clear_memory()
            
            return jsonify({
                'success': True,
                'message': 'All memories erased. I am reborn!'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/bulk-teach', methods=['POST'])
    def bulk_teach():
        """Bulk teach multiple facts"""
        data = request.json
        facts = data.get('facts', [])
        
        if not isinstance(facts, list) or not facts:
            return jsonify({'error': 'Expected list of facts'}), 400
        
        try:
            agent = get_agent()
            results = []
            
            for fact in facts:
                if isinstance(fact, str) and fact.strip():
                    response = agent.process_input(fact.strip())
                    results.append({
                        'fact': fact,
                        'success': True,
                        'mood': agent.brain.emotional_state
                    })
            
            return jsonify({
                'success': True,
                'taught': len(results),
                'results': results[-10:],
                'stats': agent.get_stats()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========== QUESTION ANSWERING ==========

    @app.route('/api/ask', methods=['POST'])
    def ask():
        """Answer a question"""
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Empty question'}), 400
        
        try:
            agent = get_agent()
            
            if not agent.question_answerer.is_question(question):
                question += "?"  # Ensure it's recognized as question
            
            answer = agent.question_answerer.answer_question(question)
            confidence = agent.question_answerer.get_answer_confidence(
                agent.question_answerer.extract_question_focus(question)
            )
            
            return jsonify({
                'success': True,
                'question': question,
                'answer': answer,
                'confidence': round(confidence, 2),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========== WEB LEARNING ==========

    @app.route('/api/learn-url', methods=['POST'])
    def learn_url():
        """Learn from a web page"""
        data = request.json
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL required'}), 400
        
        try:
            agent = get_agent()
            response = agent.learn_from_url(url)
            stats = agent.get_stats()
            
            return jsonify({
                'success': True,
                'response': response,
                'stats': stats,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/learn-text', methods=['POST'])
    def learn_text():
        """Learn from raw text"""
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        try:
            agent = get_agent()
            response = agent.learn_from_text(text)
            stats = agent.get_stats()
            
            return jsonify({
                'success': True,
                'response': response,
                'stats': stats,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analyze-text', methods=['POST'])
    def analyze_text():
        """Analyze text for facts"""
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Text required'}), 400
        
        try:
            agent = get_agent()
            analysis = agent.recursive_learner.analyze_text(text)
            
            return jsonify({
                'success': True,
                'analysis': analysis,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========== IMAGINATION & CREATIVITY ==========

    @app.route('/api/imagine', methods=['GET'])
    def imagine():
        """Generate imaginative thoughts"""
        try:
            agent = get_agent()
            topic = request.args.get('topic', None)
            
            imagination = agent.imagine(topic)
            
            return jsonify({
                'success': True,
                'imagination': imagination,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/theorize', methods=['GET'])
    def theorize():
        """Generate theories"""
        try:
            agent = get_agent()
            topic = request.args.get('topic', None)
            
            theory = agent.theorize(topic)
            
            return jsonify({
                'success': True,
                'theory': theory,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analogies', methods=['GET'])
    def analogies():
        """Find analogies"""
        try:
            agent = get_agent()
            topic1 = request.args.get('topic1', None)
            topic2 = request.args.get('topic2', None)
            
            if not topic1:
                return jsonify({'error': 'topic1 required'}), 400
            
            analogs = agent.get_analogies(topic1, topic2)
            
            return jsonify({
                'success': True,
                'analogies': analogs,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========== CONVERSATION & PERSONALITY ==========

    @app.route('/api/personality', methods=['GET'])
    def personality():
        """Get agent personality"""
        try:
            agent = get_agent()
            personality = agent.get_personality()
            
            return jsonify({
                'success': True,
                'personality': personality,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/thoughts', methods=['GET'])
    def thoughts():
        """Get autonomous thoughts"""
        try:
            agent = get_agent()
            thought = agent.autonomous_thought()
            
            return jsonify({
                'success': True,
                'thought': thought or 'I have nothing to contemplate right now...'
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/history', methods=['GET'])
    def history():
        """Get conversation history"""
        try:
            agent = get_agent()
            limit = request.args.get('limit', 20, type=int)
            
            recent_history = agent.memory.conversation_history[-limit:]
            
            return jsonify({
                'success': True,
                'history': recent_history,
                'total': len(agent.memory.conversation_history),
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/analyze/<topic>', methods=['GET'])
    def analyze(topic):
        """Analyze a topic"""
        try:
            agent = get_agent()
            analysis = agent.analyze_topic(topic)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export', methods=['GET'])
    def export():
        """Export all knowledge"""
        try:
            agent = get_agent()
            exported = agent.export_memory()
            
            return jsonify({
                'success': True,
                'data': exported
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/crawl', methods=['POST'])
    def crawl():
        """Crawl a URL, learn from it, return structured evaluation"""
        data  = request.json or {}
        url   = data.get('url', '').strip()
        depth = int(data.get('depth', 1))
        pages = int(data.get('max_pages', 8))

        if not url:
            return jsonify({'error': 'url required'}), 400
        if not url.startswith('http'):
            return jsonify({'error': 'url must start with http:// or https://'}), 400

        try:
            agent = get_agent()
            from jarvix.web_crawler import WebCrawler
            crawler = WebCrawler(agent,
                                 max_depth=min(depth, 2),
                                 max_pages=min(pages, 15))
            report   = crawler.crawl(url)
            eval_    = crawler.build_evaluation(report)
            return jsonify({'success': True, 'evaluation': eval_,
                            'stats': agent.get_stats()})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/graph', methods=['GET'])
    def graph_data():
        """Return knowledge graph as nodes + edges for 2D visualisation"""
        try:
            agent = get_agent()
            g     = agent.brain.graph

            # Build colour map by relation type
            REL_COLOR = {
                'is_a': '#667eea', 'instance_of': '#764ba2',
                'has_property': '#00b894', 'has': '#00cec9',
                'can': '#fdcb6e', 'causes': '#e17055',
                'part_of': '#6c5ce7', 'definition': '#74b9ff',
                'named': '#fd79a8', 'opposite_of': '#d63031',
                'related_to': '#b2bec3',
            }

            nodes = []
            for name, nd in g.nodes.items():
                # Count edges touching this node
                degree = sum(1 for (s, r, o) in g.edges
                             if s == name or o == name)
                nodes.append({
                    'id':    name,
                    'label': name,
                    'type':  nd.node_type,
                    'size':  max(6, min(24, 6 + degree * 2)),
                })

            edges = []
            for (s, r, o), data in g.edges.items():
                edges.append({
                    'source':     s,
                    'target':     o,
                    'relation':   r,
                    'confidence': round(data.confidence, 2),
                    'inferred':   data.inferred,
                    'color':      REL_COLOR.get(r, '#b2bec3'),
                })

            return jsonify({
                'success': True,
                'nodes':   nodes,
                'edges':   edges,
                'stats': {
                    'nodes':    len(nodes),
                    'edges':    len(edges),
                    'inferred': sum(1 for e in edges if e['inferred']),
                }
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check"""
        return jsonify({
            'status': 'healthy',
            'service': 'jarvix-v2',
            'version': '2.0.0'
        })

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
