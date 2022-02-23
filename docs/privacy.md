# privacy

!!! tldr "tl;dr"
    Using a trustworthy VPN for all your remotely fun internet traffic is a good idea. It is cheap and easy these days, and it offers multiple levels of general protection.

I have tried very hard to ensure the hydrus network servers respect your privacy. They do not work like normal websites, and the amount of information your client will reveal to them is very limited. For most general purposes, normal users can rest assured that their activity on a repository like the Public Tag Repository (PTR) is effectively completely anonymous.

You need an account to connect, but all that really means serverside is a random number with a random passcode. Your client tells nothing more to the server than the exact content you upload to it (e.g. tag mappings, which are a tag+file_hash pair). The server cannot help but be aware of your IP address to accept your network request, but in all but one situation--uploading a file to a file repository when the administrator has set to save IPs for DMCA purposes--it forgets your IP as soon as the job is done.

So that janitors can process petitions efficiently and correct mistakes, servers remember which accounts upload which content, but they do not communicate this to any place, and the memory only lasts for a certain time--after which the content is completely anonymised. The main potential privacy worries are over a malicious janitor or--more realistically, since the janitor UI is even more buggy and feature-poor than the hydrus front-end!--a malicious server owner or anyone else who gains raw access to the server's raw database files or its code as it operates. Even in the case where you cannot trust the server you are talking to, hydrus should be _fairly_ robust, simply because the client does not say much to the server, nor that often. The only realistic worries, as I talk about in detail below, are if you actually upload personal files or tag personal files with real names. I can't do much about being Anon if you (accidentally or not), declare who you are.

So, in general, if you are on a good VPN and tagging anime babes from boorus, I think we are near perfect on privacy. That said, our community is rightly constantly thinking about this topic, so in the following I have tried to go into exhaustive detail. Some of the vulnerabilities are impractical and esoteric, but if nothing else it is fun to think about. If you can think of more problems, or decent mitigations, let me know!

## https certificates { id="https_certificates" }

Hydrus servers only communicate in https, so anyone who is able to casually observe your traffic (say your roommate cracked your router, or the guy running the coffee shop whose wifi you are using likes to snoop) should not ever be able to see what data you are sending or receiving. If you do not use a VPN, they will be able to see that you _are_ talking to the repository (and the repository will technically see who you are, too, though as above, it normally isn't interested). Someone more powerful, like your ISP or Government, may be able to do more:

**If you just start a new server yourself**
:   
    When you first make a server, the 'certificate' it creates to enable https is a low quality one. It is called 'self-signed' because it is only endorsed by itself and it is not tied to a particular domain on the internet that everyone agrees on via DNS. Your traffic to this server is still encrypted, but an advanced attacker who stands between you and the server could potentially perform what is called a man-in-the-middle attack and see your traffic.
    
    This problem is fairly mitigated by using a VPN, since even if someone were able to MitM your connection, they know no more than your VPN's location, not your IP.
    
    _A future version of the network will further mitigate this problem by having you enter unverified certificates into a certificate manager and then compare to that store on future requests, to try to detect if a MitM attack is occurring._
    
**If the server is on a domain and now uses a proper verified certificate**
:   
    If the admin hosts the server on a website domain (rather than a raw IP address) and gets a proper certificate for that domain from a service like Let's Encrypt, they can swap that into the server and then your traffic should be protected from any eavesdropper. It is still good to use a VPN to further obscure _who_ you are, including from the server admin.
    

You can check how good a server's certificate is by loading its base address in the form `https://host:port` into your browser. If it has a nice certificate--like the [PTR](https://ptr.hydrus.network:45871/)--the welcome page will load instantly. If it is still on self-signed, you'll get one of those 'can't show this page unless you make an exception' browser error pages before it will show.

## accounts { id="accounts" }

An account has two hex strings, like this:

*   **Access key: `4a285629721ca442541ef2c15ea17d1f7f7578b0c3f4f5f2a05f8f0ab297786f`**
    
    This is in your _services->manage services_ panel, and acts like a password. Keep this absolutely secret--only you know it, and no one else ever needs to. If the server has not had its code changed, it does not actually know this string, but it is stores special data that lets it _verify_ it when you 'log in'.
    
*   **Account ID: `207d592682a7962564d52d2480f05e72a272443017553cedbd8af0fecc7b6e0a`**
    
    This can be copied from a button in your _services->review services_ panel, and acts a bit like a semi-private username. Only janitors should ever have access to this. If you ever want to contact the server admin about an account upgrade or similar, they will need to know this so they can load up your account and alter it.
    

When you generate a new account, the client first asks the server for a list of available auto-creatable account types, then asks for a registration token for one of them, then uses the token to generate an access key. The server is never told anything about you, and it forgets your IP address as soon as it finishes talking to you.

Your account also stores a bandwidth use record and some miscellaneous data such as when the account was created, if and when it expires, what permissions and bandwidth rules it has, an aggregate score of how often it has petitions approved rather than denied, and whether it is currently banned. I do not think someone inspecting the bandwidth record could figure out what you were doing based on byte counts (especially as with every new month the old month's bandwidth records are compressed to just one number) beyond the rough time you synced and whether you have done much uploading. Since only a janitor can see your account and could feasibly attempt to inspect bandwidth data, they would already know this information.

## downloading { id="downloading" }

When you sync with a repository, your client will download and then keep up to date with all the metadata the server knows. This metadata is downloaded the same way by all users, and it comes in a completely anonymous format. The server does not know what you are interested in, and no one who downloads knows who uploaded what. Since the client regularly updates, a detailed analysis of the raw update files will reveal roughly when a tag or other row was added or deleted, although that timestamp is no more precise than the duration of the update period (by default, 100,000 seconds, or a little over a day).

Your client will never ask the server for information about a particular file or tag. You download everything in generic chunks, form a local index of that information, and then all queries are performed on your own hard drive with your own CPU.

By just downloading, even if the server owner were to identify you by your IP address, all they know is that you sync. They cannot tell anything about your files.

In the case of a file repository, you client downloads all the thumbnails automatically, but then you download actual files separately as you like. The server does not log which files you download.

## uploading { id="uploading" }

When you upload, your account is temporarily linked to the rows of content you add. This is so janitors can group petitions by who makes them, undo large mistakes easily, and even leave you a brief message (like "please stop adding those clothing siblings") for your client to pick up the next time it syncs your account. After the temporary period is over, all submissions are anonymised. So, what are the privacy concerns with that? Isn't the account 'Anon'?

[Privacy can be tricky](https://en.wikipedia.org/wiki/AOL_search_data_leak). Hydrus tech is obviously far, far better than anything normal consumers use, but here I believe are the remaining barriers to pure Anonymity, assuming someone with resources was willing to put a lot of work in to attack you:

!!! note
    I am using the PTR as the example since that is what most people are using. If you are uploading to a server run between friends, privacy is obviously more difficult to preserve--if there are only three users, it may not be too hard to figure out who is uploading the NarutoXSonichu diaperfur content! If you are talking to a server with a small group of users, don't upload anything crazy or personally identifying unless that's the point of the server.

*   #### IP Address Across Network
    
    _Attacker:_ ISP/Government.
    
    _Exposure:_ That you use the PTR.
    
    _Problem:_ Your IP address may be recorded by servers in between you and the PTR (e.g. your ISP/Government). Anyone who could convert that IP address and timestamp into your identity would know you were a PTR user.
    
    _Mitigation:_ Use a trustworthy VPN.
    
*   #### IP Address At PTR
    
    _Attacker:_ PTR administrator or someone else who has access to the server as it runs.
    
    _Exposure:_ Which PTR account you are.
    
    _Problem:_ I may be lying to you about the server forgetting IPs, or the admin running the PTR may have secretly altered its code. If the malicious admin were able to convert IP address and timestamp into your identity, they obviously be able to link that to your account and thus its various submissions.
    
    _Mitigation:_ Use a trustworthy VPN.
    
*   #### Time Identifiable Uploads
    
    _Attacker:_ Anyone with an account on the PTR.
    
    _Exposure:_ That you use the PTR.
    
    _Problem:_ If a tag was added way before the file was public, then it is likely the original owner tagged it. An example would be if you were an artist and you tagged your own work on the PTR two weeks before publishing the work. Anyone who looked through the server updates carefully and compared to file publish dates, particularly if they were targeting you already, could notice the date discrepancy and know you were a PTR user.
    
    _Mitigation:_ Don't tag any file you plan to share if you are currently the only person who has any copies. Upload it, then tag it.
    
*   #### Content Identifiable Uploads
    
    _Attacker:_ Anyone with an account on the PTR.
    
    _Exposure:_ That you use the PTR.
    
    _Problem:_ All uploads are shared anonymously with other users, but if the content itself is identifying, you may be exposed. An example would be if there was some popular lewd file floating around of you and your girlfriend, but no one knew who was in it. If you decided to tag it with accurate 'person:' tags, anyone synced with the PTR, when they next looked at that file, would see those person tags. The same would apply if the file was originally private but then leaked.
    
    _Mitigation:_ Just like an imageboard, do not upload any personally identifying information.
    
*   #### Individual Account Cross-referencing
    
    _Attacker:_ PTR administrator or someone else with access to the server database files after one of your uploads has been connected to your real identity, perhaps with a Time/Content Identifiable Upload as above.
    
    _Exposure:_ What you have been uploading recently.
    
    _Problem:_ If you accidentally tie your identity to an individual content row (could be as simple as telling an admin 'yes, I, person whose name you know, uploaded that sibling last week'), then anyone who can see which accounts uploaded what will obviously be able to see your other uploads.
    
    _Mitigation:_ Best practise is to not to reveal specifically what you upload. **Note that this vulnerability (an admin looking up what else you uploaded after they discover something else you did) is now well mitigated by the account history anonymisation as below (assuming the admin has not altered the code to disable it!). If the server is set to anonymise content after 90 days, then your account can only be identified from specific content rows that were uploaded in the past 90 days, and cross-references would also only see the last 90 days of activity.**
    
*   #### Big Brain Individual Account Mapping Fingerprint Cross-referencing
    
    _Attacker:_ Someone who has access to tag/file favourite lists on another site and gets access to a hydrus repository that has been compromised to not anonymise history for a long duration.
    
    _Exposure:_ Which PTR account another website's account uses.
    
    _Problem:_ Someone who had raw access to the PTR database's historical account record (i.e. they had disabled the anonymisation routine below) and also had compiled some booru users' 'favourite tag/artist' lists and was very clever could try to cross reference those two lists and connect a particular PTR account to a particular booru account based on similar tag distributions. There would be many holes in the PTR record, since only the first account to upload a tag mapping is linked to it, but maybe it would be possible to get high confidence on a match if you have really distinct tastes. Favourites lists are probably decent digital fingerprints, and there may be a shadow of that in your PTR uploads, although I also think there are enough users uploading and 'competing' for saved records on different tags that each users' shadow would be too indistinct to really pull this off.
    
    _Mitigation:_ I am mostly memeing here. But privacy is tricky, and who knows what the scrapers of the future are going to do with all the cloud data they are sucking up. **Even then, the historical anonymisation routine below now generally eliminates this threat**, assuming the server has not been compromised to disable it, so it matters far less if its database files fall into bad hands in the future, but accounts on regular websites are already being aggregated by the big marketing engines, and this will only happen in more clever ways in future. I wouldn't be surprised if booru accounts are soon being connected to other online identities based on fingerprint profiles of likes and similar. Don't save your spicy favourites on a website, even if that list is private, since if that site gets hacked or just bought out one day, someone really smart could start connecting dots ten years from now.
    

## account history anonymisation { id="account_history" }

As the PTR moved to multiple accounts, we talked more about the potential account cross-referencing worries. The threats are marginal today, but it may be a real problem in future. If the server database files were to ever fall into bad hands, having a years-old record of who uploaded what is not excellent. Like the AOL search leak, that data may have unpleasant rammifications, especially to an intelligent scraper in the future. This historical record is also not needed for most janitorial work.

Therefore, hydrus repositories now completely anonymise all uploads after a certain delay. It works by assigning ownership of every file, mapping, or tag sibling/parent to a special 'null' account, so all trace that your account uploaded any of it is deleted. It happens by default 90 days after the content is uploaded, but it can be more or less depending on the local admin and janitors. You can see the current 'anonymisation' period under _review services_.

If you are a janitor with the ability to modify accounts based on uploaded content, you will see anything old will bring up the null account. It is specially labelled, so you can't miss it. You cannot ban or otherwise alter this account. No one can actually use it.
