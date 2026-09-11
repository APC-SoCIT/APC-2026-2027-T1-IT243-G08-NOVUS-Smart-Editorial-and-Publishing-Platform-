/**
 * Legal documents for BOSS Magazine PH.
 *
 * These are drafted against Philippine law — principally the Data Privacy Act
 * of 2012 (RA 10173) and the Consumer Act (RA 7394) — and are appropriate as
 * an academic deliverable. They have not been reviewed by counsel. Before the
 * platform processes real reader data or takes real payment, BOSS Media
 * Philippines Inc. should have them reviewed and should check whether it must
 * register its data processing system with the National Privacy Commission.
 */

export const ORG = {
  company: 'BOSS Media Philippines Inc.',
  brand: 'BOSS Magazine PH',
  platform: 'NOVUS',
  email: 'privacy@bossmagazineph.com',
  dpo: 'Data Protection Officer, BOSS Media Philippines Inc.',
  effective: '10 September 2026',
}

const REVIEW_NOTE = {
  type: 'notice',
  body: `This document was prepared for the NOVUS platform and reflects the
    system as built. It is not a substitute for legal advice. ${ORG.company}
    should obtain professional review before relying on it commercially.`,
}

export const DOCS = {
  privacy: {
    title: 'Privacy Policy',
    summary: `How ${ORG.company} collects, uses, and protects personal
      information on ${ORG.brand} and the ${ORG.platform} editorial platform.`,
    sections: [
      REVIEW_NOTE,
      {
        heading: 'Who we are',
        body: `${ORG.company} ("we", "us") publishes ${ORG.brand} and operates
          the ${ORG.platform} editorial platform. We are the personal
          information controller for the data described here, as that term is
          used in the Data Privacy Act of 2012 (Republic Act No. 10173).`,
      },
      {
        heading: 'Information we collect',
        list: [
          'Account details you give us: name, email address, and a password, which we store only as a cryptographic hash and never in readable form.',
          'Editorial content you create if you are a member of staff: articles, drafts, revision notes, messages, and uploaded images or layout files.',
          'Subscription status: whether your account is a free reader or a subscriber, and the dates that status changed.',
          'Technical data necessary to operate the service: your session token, and server logs recording requests, timestamps, and error conditions.',
        ],
      },
      {
        heading: 'What we do not collect',
        list: [
          'We do not use advertising cookies, third-party trackers, or analytics that profile you across other websites.',
          'We do not collect payment card details. When subscription payments are introduced, card data will be handled entirely by our payment processor and will never reach our servers.',
          'We do not sell, rent, or trade personal information to anyone.',
        ],
      },
      {
        heading: 'Why we process it, and on what basis',
        body: `We process your information to provide the service you have asked
          for — showing you articles, keeping you signed in, and letting
          editorial staff do their work. Our lawful basis is the performance of
          our contract with you under Section 12(b) of the Data Privacy Act,
          and our legitimate interest in operating a secure publication under
          Section 12(f). Where we rely on consent, such as for optional
          notifications, you may withdraw it at any time.`,
      },
      {
        heading: 'Automated evaluation of submitted articles',
        body: `Articles submitted by our writers are assessed by an automated
          system before an editor reviews them. That system scores grammar and
          readability and suggests improvements. It applies only to editorial
          content produced by our staff, never to information about readers.
          The result is advisory: an editor may override any verdict, and every
          override is recorded with a written justification. No editorial
          decision is made by automated means alone.`,
      },
      {
        heading: 'Who else processes your information',
        body: `We use a small number of service providers, each of which
          processes data only on our instructions:`,
        list: [
          'A managed PostgreSQL database provider, which stores our records.',
          'An artificial intelligence provider, which receives article text for evaluation. It does not receive reader information.',
          'An object storage provider, which holds uploaded images and magazine layouts.',
          'A payment processor and an email delivery provider, once those features are enabled.',
        ],
      },
      {
        heading: 'Transfers outside the Philippines',
        body: `Some of these providers operate servers outside the Philippines.
          Where that is so, we remain accountable for your information and
          require contractual protections consistent with Sections 20 and 21 of
          the Data Privacy Act.`,
      },
      {
        heading: 'How long we keep it',
        list: [
          'Account information: for as long as your account is open, and up to twelve months afterwards so that we can respond to disputes.',
          'Published editorial content: indefinitely, as part of the magazine’s archive and public record.',
          'Server logs: ninety days.',
          'Withdrawn or unpublished drafts: retained for editorial reference and deleted on request where we have no legal reason to keep them.',
        ],
      },
      {
        heading: 'Your rights',
        body: `Under the Data Privacy Act you have the right to be informed, to
          access your information, to object to its processing, to have
          inaccurate information corrected, to have it erased or blocked in the
          circumstances the Act provides, to data portability, and to be
          indemnified for damage caused by false or unauthorised use. To
          exercise any of these, write to ${ORG.email}. We will respond within
          fifteen working days. If you are not satisfied, you may complain to
          the National Privacy Commission.`,
      },
      {
        heading: 'Security',
        body: `Access to the platform requires authentication, and every
          state-changing action is checked against the role your account holds.
          Passwords are hashed. Traffic is encrypted in transit. Uploaded files
          are validated by type and size. No system is perfectly secure, and we
          will notify you and the National Privacy Commission of any breach
          that is likely to put your rights at serious risk, as Section 20(f)
          requires.`,
      },
      {
        heading: 'Children',
        body: `The service is intended for readers aged eighteen and over. We do
          not knowingly collect information from children. If you believe a
          child has given us personal information, write to ${ORG.email} and we
          will delete it.`,
      },
      {
        heading: 'Changes',
        body: `If we change this policy materially we will say so on this page
          and update the effective date. Continuing to use the service after a
          change means you accept the revised policy.`,
      },
      {
        heading: 'Contact',
        body: `${ORG.dpo} — ${ORG.email}`,
      },
    ],
  },

  terms: {
    title: 'Terms of Service',
    summary: `The agreement between you and ${ORG.company} governing your use
      of ${ORG.brand} and the ${ORG.platform} platform.`,
    sections: [
      REVIEW_NOTE,
      {
        heading: 'Agreement',
        body: `By using ${ORG.brand} you agree to these terms. If you do not
          agree, please do not use the service. These terms are governed by the
          laws of the Republic of the Philippines, and any dispute is subject to
          the exclusive jurisdiction of the courts of Metro Manila.`,
      },
      {
        heading: 'Who may use the service',
        body: `You must be at least eighteen years old, or have the consent of a
          parent or guardian, to create an account. Editorial accounts are
          issued by ${ORG.company} to its staff and contributors and may not be
          shared or transferred.`,
      },
      {
        heading: 'Your account',
        list: [
          'You are responsible for keeping your password confidential and for activity carried out under your account.',
          'Tell us promptly if you believe your account has been used without your permission.',
          'We may suspend an account that is used in breach of these terms, and will tell you why where we lawfully can.',
        ],
      },
      {
        heading: 'Free and subscriber access',
        body: `Some articles are free to read without an account. Others are
          available to subscribers. We may change which articles are free, and
          may add, alter, or withdraw subscription plans. Where a change affects
          a subscription you have already paid for, it will not take effect
          until your current term ends.`,
      },
      {
        heading: 'Acceptable use',
        body: 'You agree not to:',
        list: [
          'Reproduce, redistribute, or resell our articles or digital issues without written permission.',
          'Attempt to defeat the subscription paywall or gain access to material you have not paid for.',
          'Interfere with the service, probe it for vulnerabilities, or place unreasonable load on it.',
          'Upload anything unlawful, defamatory, infringing, or malicious.',
        ],
      },
      {
        heading: 'Editorial content and intellectual property',
        body: `Articles, photography, layouts, and the ${ORG.brand} name and
          marks belong to ${ORG.company} or its licensors and are protected
          under the Intellectual Property Code (Republic Act No. 8293). Brief
          quotation with attribution is permitted; systematic copying is not.`,
      },
      {
        heading: 'Content submitted by contributors',
        body: `If you are a writer, editor, designer, or other contributor, you
          confirm that the work you submit is yours, that you have the right to
          submit it, and that it does not infringe anyone else’s rights. You
          grant ${ORG.company} the right to edit, publish, and archive it in
          print and digital form. Contributors are responsible for the accuracy
          of what they write.`,
      },
      {
        heading: 'Automated editorial assessment',
        body: `Submitted articles are assessed by an automated system before
          editorial review. Scores and suggestions produced by that system are
          advisory. Editorial decisions rest with our editors, who may override
          any automated verdict with a recorded justification.`,
      },
      {
        heading: 'Availability',
        body: `We aim to keep the service available but do not guarantee
          uninterrupted access. We may suspend it for maintenance, and will give
          notice where practicable.`,
      },
      {
        heading: 'Liability',
        body: `We provide the service with reasonable care and skill. To the
          extent Philippine law permits, we are not liable for indirect or
          consequential loss, or for loss of profit, revenue, or data. Nothing
          here excludes liability that cannot lawfully be excluded, including
          liability for fraud or for death or personal injury caused by
          negligence.`,
      },
      {
        heading: 'Ending the agreement',
        body: `You may close your account at any time. We may end your access if
          you breach these terms materially. Sections concerning intellectual
          property, liability, and governing law survive termination.`,
      },
      {
        heading: 'Changes',
        body: `We may revise these terms. Material changes will be announced on
          this page with a revised effective date.`,
      },
      { heading: 'Contact', body: ORG.email },
    ],
  },

  cookies: {
    title: 'Cookie Policy',
    summary: 'What we store in your browser, why, and how to control it.',
    sections: [
      REVIEW_NOTE,
      {
        heading: 'Our approach',
        body: `We use as little browser storage as the service can function
          with. We do not use advertising cookies, and we do not use analytics
          that follow you to other websites.`,
      },
      {
        heading: 'Strictly necessary',
        body: `These are required for the service to work and cannot be turned
          off without breaking it:`,
        list: [
          'Authentication tokens, stored in your browser’s local storage, which keep you signed in and identify which account is making each request. They are cleared when you sign out.',
          'A record of your cookie choice, so that we do not ask you again on every page.',
        ],
      },
      {
        heading: 'Functional',
        list: [
          'Interface preferences, such as the category you last filtered by, so the site behaves consistently between visits.',
        ],
      },
      {
        heading: 'What we do not use',
        list: [
          'Advertising or retargeting cookies.',
          'Cross-site tracking or fingerprinting.',
          'Third-party social media pixels.',
        ],
      },
      {
        heading: 'Controlling storage',
        body: `You can clear browser storage at any time through your browser’s
          settings. Doing so will sign you out. Blocking storage entirely will
          prevent you from signing in, since we cannot maintain a session
          without it. You may still read free articles without an account.`,
      },
      { heading: 'Contact', body: ORG.email },
    ],
  },

  refunds: {
    title: 'Refund Policy',
    summary: 'When a subscription can be refunded, and how to ask for one.',
    sections: [
      REVIEW_NOTE,
      {
        type: 'notice',
        body: `Online subscription payments are not yet available. This policy
          describes how refunds will operate once they are introduced, and is
          published in advance so that terms are clear before any money changes
          hands.`,
      },
      {
        heading: 'Cooling-off period',
        body: `You may cancel a new subscription within seven days of purchase
          and receive a full refund, provided you have not downloaded a digital
          issue during that period. This is offered voluntarily and is in
          addition to your rights under the Consumer Act of the Philippines
          (Republic Act No. 7394).`,
      },
      {
        heading: 'After the cooling-off period',
        list: [
          'Monthly subscriptions: cancel at any time. Access continues to the end of the paid month; we do not refund part of a month.',
          'Annual subscriptions: cancel at any time. Where more than one month remains, we refund the unused whole months, less any months in which a digital issue was downloaded.',
        ],
      },
      {
        heading: 'When we will refund in full',
        list: [
          'You were charged more than once for the same period.',
          'You were charged after cancelling.',
          'A digital issue you paid for was not delivered and we could not resolve it.',
          'The service was unavailable for a prolonged period through our fault.',
        ],
      },
      {
        heading: 'When we will not refund',
        list: [
          'You changed your mind after the cooling-off period and have used the subscription.',
          'Your account was suspended for a serious breach of our terms.',
          'You are dissatisfied with editorial content, which is a matter of judgement rather than a defect.',
        ],
      },
      {
        heading: 'How to request one',
        body: `Write to ${ORG.email} with the email address on your account and
          the reason for the request. We will respond within five working days.
          Approved refunds are returned by the method used to pay, and typically
          appear within seven to fourteen banking days depending on your
          provider.`,
      },
      {
        heading: 'Cancelling',
        body: `You can cancel from your account settings at any time.
          Cancelling stops future billing; it does not itself trigger a refund
          of the current term.`,
      },
      { heading: 'Contact', body: ORG.email },
    ],
  },
}
