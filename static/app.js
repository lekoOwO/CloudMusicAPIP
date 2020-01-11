document.body.classList.remove('nojs');
document.body.classList.add('js');
Object.defineProperty(document, "referrer", {get : function(){ return "http://music.163.com"; }});

$(() => {
    function hasTouch() {
        return (('ontouchstart' in window) || // html5 browsers
            (navigator.maxTouchPoints > 0) || // future IE
            (navigator.msMaxTouchPoints > 0)); // current IE10
    }

    var $body = $('body');
    var base = location.protocol + '//' + location.host + '/';
    var errors = ['', '音樂數據解析失敗'];
    var preview = document.getElementById('preview');

    var app = new Vue({
        el: '#app',
        data: {
            verified: $body.data('verified'),
            error: '',

            src_url: '',
            rate: 320000,

            lyricMode: 'origin',

            url: '',
            playerUrl: null,

            song: {},
            type: 'song',
            songlist: []
        },
        methods: {
            sign(e){
                e.preventDefault();
                this.url = '';
                var data = $('#sign', this.$el).serialize();
                var songId = this.src_url;
                if (!/^\d+$/.test(songId)) {
                    // xxx/song/12345
                    // xxx/song?id=12345
                    let m = songId.match(/(?:\?id=|\/)(\d+)/);
                    if (m && m.length > 0) {
                        songId = m[1];
                    } else {
                        this.error = "無效的 ID 或無法辨識的網址";
                        return;
                    }
                }
                this.playerUrl = `${window.location.protocol}//${window.location.hostname}/?music_id=${songId}&bitrate=${this.rate.toString().slice(0,3)}`;

                var param = songId + '/' + this.rate;

                if (this.type == 'song') {
                    $.post('/sign/' + param, data, response => {
                        this.verified = response.verified;
                        if (!response.verified) {
                            this.error = '請填寫驗證碼!';
                            loadCaptcha();
                            return;
                        }
    
                        if (response.errno) {
                            this.error = errors[response.errno];
                            return;
                        }
                        
                        let SongArtist = response.song.artist.map(a => a.name).join(' / ')
    
                        this.lyric = response.song.lyric
                        
                        if (this.cp) {
                            // this.cp.remove(this.cp.playlist[0]);
                            this.cp.add({
                                name: response.song.name,
                                artist: SongArtist,
                                src: base + param + '/' + response.sign,
                                poster: response.song.album.picUrl,
                                lyric: this.lyric.origin,
                                sublyric: this.lyric.cht
                        })} else {
                        this.cp = new cplayer({
                            element: document.getElementById('cplayer'),
                            size: "110%",
                            width:"100%",
                            playlist: [{
                                name: response.song.name,
                                artist: SongArtist,
                                src: base + param + '/' + response.sign,
                                poster: response.song.album.picUrl,
                                lyric: this.lyric.origin,
                                sublyric: this.lyric.cht
                            }]
                        })}
    
                        this.url = base + param + '/' + response.sign;
                        this.song = response.song;
                        this.album = response.song.album;
                        this.error = '';
                        this.response = response;
                        this.SongArtist = SongArtist;
                    }).fail(() => {
                        this.error = "伺服器錯誤。";
                    });
                } else if (this.type == "songlist") {
                    $.post('/signList/' + param, data, response => {
                        this.verified = response.verified;
                        if (!response.verified) {
                            this.error = '請填寫驗證碼!';
                            loadCaptcha();
                            return;
                        }

                        if (response.errno) {
                            this.error = errors[response.errno];
                            return;
                        }
                        this.songlist = response.tracks;
                    })
                }
            },

            sel(e) {
                let target = e.currentTarget;
                target.setSelectionRange(0, target.value.length);
            },

            selRate(event){
                let dom = event.target;
                this.rate = parseInt(dom.dataset.rate);
                document.getElementById('rateText').innerHTML = dom.dataset.rate.slice(0, -3) + ' kbps';
            },

            selType(event){
                this.type = event.target.dataset.type;;
            },

            addSong(event){
                event.preventDefault();
                let dom = event.target;
                let songRate = this.rate;
                let songId = dom.dataset.songid;

                let param = songId + '/' + songRate;
                let data = $('#sign', this.$el).serialize();

                $.post('/sign/' + param, data, response => {
                    this.verified = response.verified;
                        if (!response.verified) {
                            this.error = '請填寫驗證碼!';
                            loadCaptcha();
                            return;
                        }
    
                        if (response.errno) {
                            this.error = errors[response.errno];
                            return;
                        }
                        let SongArtist = response.song.artist.map(a => a.name).join(' / ');
                        
                        if (this.cp) {
                            // this.cp.remove(this.cp.playlist[0]);
                            this.cp.add({
                                name: response.song.name,
                                artist: SongArtist,
                                src: base + param + '/' + response.sign,
                                poster: response.song.album.picUrl,
                                lyric: response.song.lyric.origin,
                                sublyric: response.song.lyric.cht
                        })} else {
                        this.cp = new cplayer({
                            element: document.getElementById('cplayer'),
                            size: "110%",
                            width:"100%",
                            playlist: [{
                                name: response.song.name,
                                artist: SongArtist,
                                src: base + param + '/' + response.sign,
                                poster: response.song.album.picUrl,
                                lyric: response.song.lyric.origin,
                                sublyric: response.song.lyric.cht
                            }]
                        })}
                })

            },

            onInput(event){
                let value = event.target.value;
                if (value.match(/(?:playlist.+?)(\d+)/)) this.type = "songlist";
                else if (value.match(/(?:song.+?)(\d+)/)) this.type = "song";
            }
        },
        created() {
            document.body.classList.add('vue');
            if (!this.verified) {
                loadCaptcha();
            }
        },
        mounted(){
            this.dropdownTriggered = this.dropdownTriggered ? true : ts('.ts.dropdown:not(.basic)').dropdown()
            getParamsFromURL()
        }
    });

    var captchaId = null;

    function loadCaptcha() {
        if (window.grecaptcha) {
            if (captchaId !== null) {
                grecaptcha.reset(captchaId);
            } else {
                captchaId = grecaptcha.render('recaptcha', {
                    'sitekey': $body.data('sitekey')
                });
            }
        } else {
            var script = document.createElement('script');
            script.src = 'https://www.google.com/recaptcha/api.js?onload=loadCaptcha&render=explicit';
            document.body.appendChild(script);
        }
    }

    window.loadCaptcha = loadCaptcha;

    function addCopy(copyBtn) {
        const clipboard = new Clipboard(copyBtn);
        copyBtn.addEventListener('click', function(e) {
            e.preventDefault();
        });
        clipboard.on('success', function() {
            Swal('成功', '複製成功！', 'success')
        }).on('error', function() {
            var action = hasTouch() ? '長按' : '右鍵';
            Swal('喔不', '複製失敗，請' + action + '網址手動複製！', 'error')
        });
    }

    addCopy(document.getElementById('copy'))
    addCopy(document.getElementById('copy2'))
});