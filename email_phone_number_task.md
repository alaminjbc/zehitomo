1. In this div In the message there give email and gmail
<div ng-class="{
          'message-container' :!message.sending,
          'pro-message-container' :isClientMode() &amp;&amp; message.from === pro.$id,
          'client-message-container' :isClientMode() &amp;&amp; message.from === client.$id,
          'pro-mode-client-message-container': isProMode() &amp;&amp; message.from === client.$id,
        }" class="message-container pro-message-container"> <!-- ngIf: !message.sending && message.from === currentUser.id --> <!-- ngIf: !message.sending && message.from !== currentUser.id --><div ng-if="!message.sending &amp;&amp; message.from !== currentUser.id" ng-class="{'pro-message-time': message.from === pro.$id, 'client-message-time': message.from === client.$id}" class="message-time ng-binding ng-scope pro-message-time">18:57</div><!-- end ngIf: !message.sending && message.from !== currentUser.id --> <span ng-class="{
            'is-me': (message.from == currentUser.id || message.sending) &amp;&amp; (message.messageType !== 'autoReplySampleMessage'),
            'cover-letter' : message.content === apply.coverLetter,
            'sample': message.messageType === 'autoReplySampleMessage'
          }" class="content cover-letter"><chat-message-content apply-id="apply.$id" apply-message="message" is-cover-letter="message.content === apply.coverLetter &amp;&amp; !isDirectBooking" is-current-user-pro="currentUser.id === apply.pro" is-own-message="message.from === currentUser.id" show-ai-identity="showAiIdentity()" class="ng-isolate-scope"><!-- ngIf: vm.applyMessage.content --><react-chat-message api-url="vm.apiUrl" apply-id="vm.applyId" is-cover-letter="vm.isCoverLetter" is-current-user-pro="vm.isCurrentUserPro" is-own-message="vm.isOwnMessage" message="vm.applyMessage" responding-to-client-message="vm.respondingToClientMessage" show-ai-identity="vm.showAiIdentity" ng-if="vm.applyMessage.content" class="ng-scope ng-isolate-scope"><span class="chat-message-content-text">ねこのハンドの五十嵐と申します。 

戸建タイプで家庭用エアコン1台、可能な限り早くとのことですので、設置状況に合わせた最適なクリーニングプランをご提案できればと思います。差し支えなければ、ご希望の曜日や時間帯を教えていただけますか？

エアコンクリーニングご検討ということで
当店のご案内させて頂きます。 

⬛︎料金＆作業時間目安
ノーマルタイプですと￥7500
作業時間50~60分 

お掃除機能ありですと￥13500
作業時間90分前後  

天井埋め込みエアコンですと￥14000
作業時間90分前後(業務用は￥18000)

＋駐車場がない場合
コインパーキング代  が追加費用となります。   

⬛︎事前にお伝えしたい事
型番をお知らせ頂けますとお掃除機能ありかどうかこちらでも確認させて頂きます。

洗い場としてお風呂場かベランダなどをお借りさせて頂きます。   

午前中希望や、土日希望、何時以降希望などあれば教えて頂けましたらこちらで空き日程ピックアップもさせて頂きます。   

何かご不明点があればお申し付け下さいませ。 ご検討よろしくお願い申し上げます。

お急ぎの方は以下連絡先まで直接ご連絡頂いても大丈夫です。
(営業目的のご連絡はお断りしております。)

＜連絡先＞
電話　：09062355760
メール：<a href="mailto:tanu-keti@ezweb.ne.jp" rel="noopener noreferrer" target="_blank">tanu-keti@ezweb.ne.jp</a>
ご不明な点がございましたら、遠慮なくご質問くださいませ。
何卒宜しくお願いします。</span><div class="ChatMessage-module__proposal-budget-container___aTLFy"><div class="ChatMessage-module__proposal-budget-left___PRUsy"><div class="ChatMessage-module__icon-container____oTgg"><img alt="Yen icon" class="ChatMessage-module__icon-yen____1K1T" src="/assets/images/icon/icon-yen-circle-blue.e6bef9b8.svg"></div><p>サービス提供価格</p></div><p>見積もり相談可</p></div></react-chat-message><!-- end ngIf: vm.applyMessage.content --> <!-- ngIf: vm.applyMessage.photos.length --> <!-- ngIf: vm.applyMessage.pdfs.length --> </chat-message-content><!-- ngIf: isProMode() && message.id === latestAiPreviewMessageId && !message.sending --> </span> <!-- ngIf: message.sending --> <br> </div>


